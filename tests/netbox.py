#!/usr/bin/env python3
"""NetBox (M013): render the pinned official chart with our values, and run the inventory reconciliation
against an in-memory NetBox.

Needs `helm` and the chart download; no cluster, NetBox or Proxmox access.
"""
import copy
import importlib.util
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/netbox"
HOST = "netbox.doku-lab.net"
SECRET = "netbox-secrets"

spec = importlib.util.spec_from_file_location("netbox_sync", ROOT / "scripts/netbox-sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def containers(doc):
    pod = doc["spec"]["template"]["spec"]
    return pod.get("initContainers", []) + pod["containers"]


def chart():
    # The chart and its version are pinned where Argo CD reads them.
    application = yaml.safe_load((ROOT / "services/argocd/apps/netbox.yaml").read_text())
    source = application["spec"]["sources"][0]
    assert re.fullmatch(r"\d+\.\d+\.\d+", source["targetRevision"]) and source["helm"]["releaseName"] == "netbox"
    result = subprocess.run(["helm", "template", "netbox", f"oci://{source['repoURL']}/{source['chart']}", "--version", source["targetRevision"],
                             "--namespace", "netbox", "-f", str(DIR / "values.yaml")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    kinds = [d["kind"] for d in docs]
    assert "Secret" not in kinds, "every credential comes from the Secret made by `make netbox-deploy`"
    assert "StatefulSet" not in kinds, "no bundled PostgreSQL or Valkey"
    deployments = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Deployment"}
    assert set(deployments) == {"netbox", "netbox-worker"}
    for name, deployment in deployments.items():
        assert deployment["spec"]["replicas"] == 1, f"{name}: one replica per service for now"
        for container in containers(deployment):
            assert "bitnami" not in container["image"] and not container["image"].endswith(":latest"), container["image"]
        main = deployment["spec"]["template"]["spec"]["containers"][0]
        assert main["image"] == "ghcr.io/netbox-community/netbox:v4.7.5" and main["resources"]["requests"]["memory"]
        assert main["securityContext"]["readOnlyRootFilesystem"] and main["securityContext"]["runAsNonRoot"]
        # Every projected secret is ours, and every key it asks for is one the Make target writes.
        (secrets,) = [v for v in deployment["spec"]["template"]["spec"]["volumes"] if v["name"] == "secrets"]
        wanted = set()
        for source in secrets["projected"]["sources"]:
            assert source["secret"]["name"] == SECRET, source
            wanted |= {item["key"] for item in source["secret"]["items"]}
        assert wanted <= secret_keys(), wanted - secret_keys()
    web_env = {e["name"]: e.get("value") for e in deployments["netbox"]["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert web_env["GRANIAN_WORKERS"] == "2"
    config = next(d for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "netbox")
    settings = yaml.safe_load(config["data"]["netbox.yaml"])
    assert settings["ALLOWED_HOSTS"] == [HOST] and settings["LOGIN_REQUIRED"] is True, "no anonymous reading of the inventory"
    assert settings["CSRF_TRUSTED_ORIGINS"] == [f"https://{HOST}"]
    database = settings["DATABASES"]["default"]
    assert (database["HOST"], database["NAME"], database["USER"]) == ("192.168.0.60", "netbox", "netbox"), "shared PostgreSQL (ADR-015)"
    assert database["OPTIONS"]["sslmode"] == "require"
    assert settings["REDIS"]["tasks"]["HOST"] == settings["REDIS"]["caching"]["HOST"] == "netbox-valkey"
    plugins(deployments, settings)
    (claim,) = [d for d in docs if d["kind"] == "PersistentVolumeClaim"]
    assert claim["metadata"]["name"] == "netbox-media" and claim["spec"]["storageClassName"] == "nvme-shared" and claim["spec"]["accessModes"] == ["ReadWriteMany"], \
        "web and worker share the media volume; live data on the NVMe storage outside k3s (ADR-012)"
    assert not [d for d in docs if d["kind"] in ("Ingress", "HTTPRoute")], "the route is in access.yaml"


def plugins(deployments, settings):
    """The diagram plugins (ADR-018): pinned files with checksums, installed once per release on a volume by an
    init container of the same image, read from there by the web and the worker; nothing else changes."""
    import hashlib

    access = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d}
    data = access[("ConfigMap", "netbox-plugins")]["data"]
    lines = data["requirements.txt"].split("\n")[:-1]
    assert all(re.fullmatch(r"[a-z-]+==\d+\.\d+\.\d+ --hash=sha256:[0-9a-f]{64}", line) for line in lines), "one pinned file each, by checksum"
    assert [line.split("==")[0] for line in lines] == ["netbox-topology-views", "netbox-floorplan-plugin", "netbox-reorder-rack"]
    assert settings["PLUGINS"] == ["netbox_topology_views", "netbox_floorplan", "netbox_reorder_rack"]
    install = data["install.sh"]
    assert "--require-hashes --no-deps --only-binary :all:" in install and "-r /config/requirements.txt" in install
    assert not re.search(r"curl|wget|pip install [a-z]|sudo|chmod", install), "nothing but the pinned files is fetched"
    claim = access[("PersistentVolumeClaim", "netbox-plugins")]["spec"]
    assert claim["storageClassName"] == "nvme-shared" and claim["accessModes"] == ["ReadWriteMany"], "web and worker read the same volume"
    # A change of NetBox's version or of the pinned files changes the release, and with it the directory read.
    release = "v4.7.5-" + hashlib.sha256((data["requirements.txt"] + install).encode()).hexdigest()[:12]
    for name, deployment in deployments.items():
        pod = deployment["spec"]["template"]["spec"]
        main = pod["containers"][0]
        (init,) = [c for c in pod["initContainers"] if c["name"] == "plugins"]
        assert init["image"] == main["image"], "the plugins are installed with the interpreter that will load them"
        assert init["command"] == ["sh", "/config/install.sh"] and init["env"] == [{"name": "PLUGINS_RELEASE", "value": release}], \
            f"{name}: the release name in values.yaml must be {release}"
        security = init["securityContext"]
        assert security["readOnlyRootFilesystem"] and security["runAsNonRoot"] and security["capabilities"] == {"drop": ["ALL"]}
        assert {m["name"]: m["mountPath"] for m in init["volumeMounts"]} == {"plugins": "/plugins", "plugins-config": "/config", "plugins-tmp": "/tmp"}
        volumes = {v["name"]: v for v in pod["volumes"]}
        assert volumes["plugins"]["persistentVolumeClaim"] == {"claimName": "netbox-plugins"} and volumes["plugins-config"]["configMap"] == {"name": "netbox-plugins"}
        mounts = {m["mountPath"]: m for m in main["volumeMounts"] if m["name"] == "plugins"}
        assert mounts["/opt/netbox/plugins"] == {"name": "plugins", "mountPath": "/opt/netbox/plugins", "subPath": f"{release}/packages", "readOnly": True}
        assert {e["name"]: e.get("value") for e in main["env"]}["PYTHONPATH"] == "/opt/netbox/plugins"
        # Only the web serves static files: NetBox's own and the plugins', from the same release.
        static = mounts.get("/opt/netbox/netbox/static")
        assert (static == {"name": "plugins", "mountPath": "/opt/netbox/netbox/static", "subPath": f"{release}/static", "readOnly": True}) == (name == "netbox")


def secret_keys():
    recipe = re.search(r"^netbox-deploy:.*?(?=^\S)", (ROOT / "Makefile").read_text(), re.M | re.S).group(0)
    line = next(l for l in recipe.splitlines() if "printf 'secret_key=" in l)
    return set(re.findall(r"(?:^|\\n|')([a-z_]+)=", line.split("printf", 1)[1]))


def access():
    docs = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d]
    assert all(d["metadata"].get("namespace", "netbox") == "netbox" for d in docs if d["kind"] != "Namespace")
    (valkey,) = [d for d in docs if d["kind"] == "Deployment"]
    (container,) = containers(valkey)
    assert valkey["spec"]["replicas"] == 1 and re.fullmatch(r"docker\.io/valkey/valkey:\d+\.\d+\.\d+-alpine", container["image"])
    assert container["env"] == [{"name": "VALKEY_PASSWORD", "valueFrom": {"secretKeyRef": {"name": SECRET, "key": "valkey_password"}}}]
    assert "--requirepass" in container["args"] and container["securityContext"]["readOnlyRootFilesystem"]
    assert not [v for v in valkey["spec"]["template"]["spec"]["volumes"] if "persistentVolumeClaim" in v], "queue and cache only"
    (route,) = [d for d in docs if d["kind"] == "IngressRoute"]
    (rule,) = route["spec"]["routes"]
    assert rule["match"] == f"Host(`{HOST}`)" and rule["middlewares"] == [{"name": "admin-lan"}] and route["spec"]["tls"] == {}
    assert rule["services"] == [{"name": "netbox", "port": 80}] and route["spec"]["entryPoints"] == ["websecure"]
    (lan,) = [d for d in docs if d["kind"] == "Middleware"]
    assert lan["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24", "10.42.0.0/16"], "the LAN and the pods of this cluster"
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == "192.168.0.40"
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert {"name": "netbox"} in apps


def sso_pipeline():
    """The step added to the sign-in pipeline (ADR-017): superuser exactly while Authentik lists the person in
    homelab-admins, and nothing written when nothing changes."""
    (config,) = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text())
                 if d and d["kind"] == "ConfigMap" and d["metadata"]["name"] == "netbox-sso-pipeline"]
    assert config["metadata"] == {"name": "netbox-sso-pipeline", "namespace": "netbox"}
    module = {}
    exec(compile(config["data"]["sso_pipeline.py"], "sso_pipeline.py", "exec"), module)  # noqa: S102 - our own file

    class User:
        def __init__(self, is_superuser):
            self.is_superuser, self.saved = is_superuser, []

        def save(self, update_fields):
            self.saved.append(update_fields)

    for groups, before, after, writes in ((["homelab-admins", "other"], False, True, 1), (["other"], True, False, 1),
                                          ("homelab-admins", False, True, 1), (["homelab-admins"], True, True, 0),
                                          (None, False, False, 0)):
        user = User(before)
        module["set_superuser"]({"groups": groups} if groups is not None else {}, user, backend=None)
        assert user.is_superuser is after and len(user.saved) == writes, (groups, before)
        assert all(fields == ["is_superuser"] for fields in user.saved)
    values = yaml.safe_load((DIR / "values.yaml").read_text())
    mount = values["extraVolumeMounts"][0]
    assert mount["mountPath"] == "/opt/netbox/netbox/netbox/sso_pipeline.py" and mount["subPath"] == "sso_pipeline.py"
    assert values["extraVolumes"][0] == {"name": "sso-pipeline", "configMap": {"name": "netbox-sso-pipeline"}}


def make_guards():
    make = (ROOT / "Makefile").read_text()
    for target, guard in (("netbox-deploy", "NETBOX_DEPLOY_APPROVED"), ("netbox-apply", "NETBOX_APPLY_APPROVED"),
                          ("netbox-identities", "NETBOX_IDENTITIES_APPROVED"), ("netbox-prune", "NETBOX_PRUNE_APPROVED")):
        recipe = re.search(rf"^{target}:.*?(?=^\S)", make, re.M | re.S).group(0)
        assert f'test "$({guard})" = yes' in recipe, target
        refused = subprocess.run(["make", "-C", str(ROOT), target], capture_output=True, text=True)
        assert refused.returncode != 0 and "Approve" in refused.stderr + refused.stdout or "approve" in refused.stderr, target
    deploy = re.search(r"^netbox-deploy:.*?(?=^\S)", make, re.M | re.S).group(0)
    assert "helm " not in deploy and "apply -f services/argocd/apps/netbox.yaml" in deploy, "Argo CD installs the chart, not Make"
    assert "NETBOX_SUPERUSER_API_TOKEN" not in make and "api_token=\\nvalkey_password" in make, "no standing superuser token"
    assert secret_keys() == {"secret_key", "api_token_peppers", "email_password", "username", "email", "password", "api_token",
                             "valkey_password", "db_password"}


class FakeNetBox:
    """Stores what is posted and filters the way the reconciliation asks. Like the real client, it cannot delete."""

    # Filters that do not carry the name of the stored field.
    PARENTS = {("ipam/services", "virtual_machine_id"): ("parent_object_type", "virtualization.virtualmachine", "parent_object_id"),
               ("ipam/services", "device_id"): ("parent_object_type", "dcim.device", "parent_object_id"),
               ("dcim/mac-addresses", "interface_id"): ("assigned_object_type", "dcim.interface", "assigned_object_id"),
               ("dcim/mac-addresses", "vminterface_id"): ("assigned_object_type", "virtualization.vminterface", "assigned_object_id")}

    def __init__(self):
        self.objects, self.writes, self.next_id = {}, [], 1

    def list(self, path, query=None):
        def matches(item):
            for key, value in (query or {}).items():
                if (path, key) in self.PARENTS:
                    kind_field, kind, id_field = self.PARENTS[(path, key)]
                    if item.get(kind_field) != kind or item.get(id_field) != value:
                        return False
                    continue
                if key.startswith("cf_"):
                    actual = item.get("custom_fields", {}).get(key[3:])
                elif key.endswith("_id"):
                    actual = item.get(key[:-3])
                else:
                    actual = item.get(key)
                if actual != value:
                    return False
            return True
        return [copy.deepcopy(item) for item in self.objects.get(path, []) if matches(item)]

    def create(self, path, body):
        item = {"id": self.next_id, **copy.deepcopy(body)}
        self.next_id += 1
        self.objects.setdefault(path, []).append(item)
        self.writes.append(("create", path, item["id"]))
        if path == "dcim/cables":  # NetBox shows the cable on both ports
            for end in item["a_terminations"] + item["b_terminations"]:
                self.get("dcim/interfaces", id=end["object_id"])["cable"] = item["id"]
        return copy.deepcopy(item)

    def update(self, path, object_id, body):
        item = next(i for i in self.objects[path] if i["id"] == object_id)
        item.update(copy.deepcopy(body))
        self.writes.append(("update", path, object_id))
        return copy.deepcopy(item)

    def get(self, path, **match):
        (item,) = [i for i in self.objects[path] if all(i.get(k) == v for k, v in match.items())]
        return item


MACHINES = [
    {"name": "k3s-server-01", "vmid": 310, "node": "pve-lab", "address": "192.168.0.40", "role": "k3s-server", "platform": "debian-13", "root": "k3s"},
    {"name": "dns-01", "vmid": 370, "node": "pve-infra", "address": "192.168.0.70", "role": "dns", "platform": "debian-13", "root": "dns"},
]
SERIAL, HOST_MAC, GUEST_MAC = "SERIAL-SYNTHETIC-1", "6C:24:08:00:00:01", "BC:24:11:00:01:36"


def guest(vmid, name, node, kind="qemu", status="running", ip=None, memory=4096, disks=(), ostype="l26"):
    return {"vmid": vmid, "name": name, "node": node, "type": kind, "status": status, "vcpus": 2, "memory_mb": memory,
            "disk_mb": 32768, "ostype": ostype, "disks": [{"name": n, "storage": "local-lvm", "size_mb": s} for n, s in disks],
            "nics": [{"name": "net0", "mac": f"BC:24:11:00:{vmid // 256:02X}:{vmid % 256:02X}", "bridge": "vmbr0", "ip": ip}]}


def snapshots():
    return {
        "doku-lab": {"age_hours": 0.1, "guests": [guest(310, "k3s-server-01", "pve-lab", ip="192.168.0.40/24", disks=[("scsi0", 65536), ("scsi1", 1024)]),
                                                   guest(370, "dns-01", "pve-infra", ip="192.168.0.70/24"),
                                                   guest(999, "scratch", "pve-core")]},
        "legacy": {"age_hours": 0.1, "guests": [guest(204, "caddy", "pve-lab", kind="lxc", ip="192.168.0.24/24", ostype="debian"),
                                                 guest(208, "deb13-monitoring", "pve-lab", status="stopped"),
                                                 guest(203, "print-server", "pve-lab", kind="lxc", status="stopped"),
                                                 guest(501, "desktop", "pve-lab", status="stopped", ostype="win11")]},
    }


def facts():
    """What scripts/host-facts.py reports for one host: pve-core, plugged into port 8 of the switch."""
    return {"pve-core": {
        "system": {"manufacturer": "LENOVO", "product": "30EF006DUS", "version": "ThinkStation P350 Tiny", "serial": SERIAL},
        "cpu": {"model": "11th Gen Intel(R) Core(TM) i7-11700 @ 2.50GHz", "sockets": 1, "cores": 8, "threads": 16},
        "memory_modules": [{"slot": "DIMM 0", "size_mb": 16384, "type": "DDR4", "speed": "3200 MT/s", "manufacturer": "Kingston",
                            "part_number": "9905700", "serial": "MEM-SYNTHETIC"},
                           {"slot": "DIMM 0", "size_mb": 16384, "type": "DDR4", "speed": "3200 MT/s", "manufacturer": "Unknown",
                            "part_number": "Unknown", "serial": "00000000"}],
        "disks": [{"name": "nvme0n1", "model": "KINGSTON SNVS1000G", "serial": "DISK-SYNTHETIC", "size_gb": 1000, "transport": "nvme"}],
        "interfaces": [{"name": "nic0", "kind": "physical", "mac": HOST_MAC, "carrier": True, "speed_mbps": 1000},
                       {"name": "vmbr0", "kind": "bridge", "mac": HOST_MAC, "carrier": True, "speed_mbps": 10000},
                       {"name": "wlo1", "kind": "wireless", "mac": "70:D8:23:00:00:01", "carrier": False, "speed_mbps": None},
                       {"name": "enx0", "kind": "physical", "mac": "00:00:5E:00:53:01", "carrier": False, "speed_mbps": None}],
        "neighbours": {"nic0": {"chassis_id": "24:5E:BE:00:00:01", "port_id": "8", "system_name": "QSW-M3216R-8S8T",
                                "management_address": "192.168.0.116"}}}}


def reconciliation():
    seed = yaml.safe_load((DIR / "inventory.yaml").read_text())
    api = FakeNetBox()

    def run(apply, machines=MACHINES, observed=None, seen=None, inventory=seed):
        return sync.reconcile(inventory, machines, snapshots() if observed is None else observed, api, apply, facts() if seen is None else seen)

    # A plan against an empty NetBox lists everything and writes nothing.
    plan = run(False)
    assert not api.writes and len(plan.operations) > 150 and all(op.startswith(("create", "update")) for op in plan.operations)
    assert "create  vm k3s-server-01" in plan.operations and "create  device pve-core" in plan.operations
    assert plan.operations.count("create  manufacturer Lenovo") == 1, "a shared object is planned once"
    assert "create  cable pve-core nic0 - switch 8" in plan.operations
    # Two machines claiming one address: the one Git defines keeps it, the other is reported (the old AdGuard
    # container still carries 192.168.0.20, which dns-01 serves now).
    clash = snapshots()
    clash["legacy"]["guests"].append(guest(200, "adguard", "pve-lab", kind="lxc", status="stopped", ip="192.168.0.20/24"))
    clashing = run(False, observed=clash)
    assert any("adguard" in line and "192.168.0.20/24 already belongs to 'address 192.168.0.20/24'" in line for line in clashing.review)
    assert not api.writes

    applied = run(True)
    assert api.writes and not hasattr(api, "delete") and not hasattr(sync.NetBox, "delete"), "the reconciliation cannot delete"
    again = run(False)
    assert again.operations == [], f"a second run changes nothing: {again.operations}"
    # Serial numbers and hardware addresses go to NetBox, never to the output.
    printed = "\n".join(plan.operations + applied.operations + applied.review)
    assert not any(value in printed for value in (SERIAL, HOST_MAC, GUEST_MAC, "MEM-SYNTHETIC", "DISK-SYNTHETIC"))

    vms, ips, ports = "virtualization/virtual-machines", "ipam/ip-addresses", "dcim/interfaces"
    tags = {t["slug"]: t["id"] for t in api.objects["extras/tags"]}
    cluster = {c["name"]: c["id"] for c in api.objects["virtualization/clusters"]}
    role = {r["slug"]: r["id"] for r in api.objects["dcim/device-roles"]}
    platform = {p["slug"]: p["id"] for p in api.objects["dcim/platforms"]}
    device = {d["name"]: d for d in api.objects["dcim/devices"]}
    k3s = api.get(vms, name="k3s-server-01")
    assert k3s["cluster"] == cluster["doku-lab"] and k3s["tags"] == [tags["iac"]]
    assert k3s["custom_fields"] == {"proxmox_vmid": 310, "defined_in": sync.SOURCE_URL + "terraform/stacks/k3s"}
    assert k3s["memory"] == 4096 and k3s["device"] == device["pve-lab"]["id"], "sizing observed, host from Git"
    address = api.get(ips, address="192.168.0.40/24")
    assert address["assigned_object_type"] == "virtualization.vminterface" and k3s["primary_ip4"] == address["id"]
    service = api.get(ips, address="192.168.0.20/24")
    assert service["role"] == "secondary" and service["assigned_object_id"] == api.get(
        "virtualization/interfaces", virtual_machine=api.get(vms, name="dns-01")["id"], name="net0")["id"]
    assert api.get(ips, address="192.168.0.60/24")["role"] == "vip" and "assigned_object_id" not in api.get(ips, address="192.168.0.60/24")
    # Disks listed one by one: NetBox adds them up, so the total is not sent; without a list the total is.
    disks = {d["name"]: d for d in api.objects["virtualization/virtual-disks"] if d["virtual_machine"] == k3s["id"]}
    assert {n: d["size"] for n, d in disks.items()} == {"scsi0": 65536, "scsi1": 1024} and "disk" not in k3s
    assert api.get(vms, name="dns-01")["disk"] == 32768
    # A guest's hardware address is its port's primary one.
    net0 = api.get("virtualization/interfaces", virtual_machine=k3s["id"], name="net0")
    mac = api.get("dcim/mac-addresses", mac_address=GUEST_MAC)
    assert (mac["assigned_object_type"], mac["assigned_object_id"]) == ("virtualization.vminterface", net0["id"]) and net0["primary_mac_address"] == mac["id"]

    # Parameters automation reads: per site, platform and role, with the values the roots enforce.
    contexts = {c["name"]: c for c in api.objects["extras/config-contexts"]}
    assert contexts["role-k3s-server"]["roles"] == [role["k3s-server"]] and contexts["role-k3s-server"]["sites"] == []
    assert contexts["role-k3s-server"]["data"]["provisioning"]["vmid_range"] == [310, 349]
    assert contexts["site-network"]["data"]["network"]["dns_servers"] == ["192.168.0.20"]
    variables = (ROOT / "terraform/stacks/k3s/variables.tf").read_text()
    assert "k3s VMIDs are 310-349" in variables and "192.168.0.40-49/24" in variables, "the context repeats what the root enforces"
    # A range is tied to the machines that use it through an IPAM role of the same slug.
    address_role = {r["slug"]: r["id"] for r in api.objects["ipam/roles"]}
    assert api.get("ipam/ip-ranges", start_address="192.168.0.40/24")["role"] == address_role["k3s-server"]
    assert "role" not in api.get("ipam/ip-ranges", start_address="192.168.0.100/24")
    # Networks that exist only inside the cluster belong to no site.
    pods = api.get("ipam/prefixes", prefix="10.42.0.0/16")
    assert pods["role"] == address_role["kubernetes"] and "scope_id" not in pods and "scope_id" in api.get("ipam/prefixes", prefix="192.168.0.0/24")
    services = {(s["parent_object_type"], s["parent_object_id"], s["name"]): s for s in api.objects["ipam/services"]}
    machine = "virtualization.virtualmachine"
    assert services[(machine, k3s["id"], "Kubernetes API")]["ports"] == [6443] and services[(machine, k3s["id"], "Ingress (Traefik)")]["ports"] == [80, 443]
    assert services[(machine, api.get(vms, name="dns-01")["id"], "DNS")]["protocol"] == "udp"
    assert services[("dcim.device", device["truenas"]["id"], "Forgejo")]["ports"] == [30142, 30143]
    # Git owns the contexts: a change made in NetBox is overwritten.
    api.get("extras/config-contexts", name="site-network")["data"] = {"network": {"gateway": "192.168.0.254"}}
    restored = run(True)
    assert any(op.startswith("update  config context site-network") for op in restored.operations)
    assert api.get("extras/config-contexts", name="site-network")["data"]["network"]["gateway"] == "192.168.0.1"
    assert run(False).operations == []

    # Hardware models: named, with their ports; a numbered range gives one port per number.
    switch_type = api.get("dcim/device-types", slug="qnap-qsw-m3216r-8s8t")
    assert switch_type["u_height"] == 1 and switch_type["model"] == "QSW-M3216R-8S8T"
    templates = {t["name"]: t["type"] for t in api.objects["dcim/interface-templates"] if t["device_type"] == switch_type["id"]}
    assert len(templates) == 17 and templates["1"] == "10gbase-t" and templates["16"] == "10gbase-x-sfpp" and templates["mgmt"] == "1000base-t"
    assert not [t for t in api.objects["dcim/device-types"] if "unknown" in t["slug"]], "no device type is called unknown"
    assert all(d["device_type"] == api.get("dcim/device-types", slug=e["type"])["id"] for e in seed["devices"] for d in [device[e["name"]]])
    # A device has the ports of its type and its own; bridge, aggregate and parent tie them together.
    port = {(p["device"], p["name"]): p for p in api.objects[ports]}
    core, nas, switch = device["pve-core"]["id"], device["truenas"]["id"], device["switch"]["id"]
    assert port[(core, "nic0")]["bridge"] == port[(core, "vmbr0")]["id"] and port[(core, "vmbr0")]["type"] == "bridge"
    assert port[(core, "amt")]["parent"] == port[(core, "nic0")]["id"] and port[(core, "amt")]["mgmt_only"] is True
    assert port[(nas, "enp1s0")]["lag"] == port[(nas, "bond0")]["id"] == port[(nas, "enp3s0")]["lag"]
    assert port[(core, "wlo1")]["enabled"] is False and len([p for p in port if p[0] == switch]) == 18
    assert device["pve-core"]["primary_ip4"] == api.get(ips, address="192.168.0.11/24")["id"]
    assert api.get(ips, address="192.168.0.11/24")["assigned_object_id"] == port[(core, "vmbr0")]["id"]
    assert api.get(ips, address="192.168.0.116/24")["status"] == "dhcp" and api.get(ips, address="192.168.0.1/24")["dns_name"] == "pfsense.doku-lab.net"
    # Observed on the host: serial number, link speed, hardware address of the physical port (not of the bridge),
    # processor, memory and disks; what the firmware calls unknown is left empty.
    assert device["pve-core"]["serial"] == SERIAL and "serial" not in device["pve-lab"]
    assert port[(core, "nic0")]["speed"] == 1000000 and "speed" not in port[(core, "vmbr0")]
    host_mac = api.get("dcim/mac-addresses", mac_address=HOST_MAC)
    assert host_mac["assigned_object_id"] == port[(core, "nic0")]["id"] and port[(core, "nic0")]["primary_mac_address"] == host_mac["id"]
    assert len([m for m in api.objects["dcim/mac-addresses"] if m["mac_address"] == HOST_MAC]) == 1
    items = {i["name"]: i for i in api.objects["dcim/inventory-items"] if i["device"] == core}
    assert set(items) == {"CPU", "Memory 1", "Memory 2", "nvme0n1"} and items["CPU"]["part_id"].startswith("11th Gen Intel")
    assert items["Memory 1"]["serial"] == "MEM-SYNTHETIC" and items["Memory 1"]["manufacturer"] == api.get("dcim/manufacturers", slug="kingston")["id"]
    assert "serial" not in items["Memory 2"] and "manufacturer" not in items["Memory 2"] and items["Memory 2"]["part_id"] == ""
    assert items["nvme0n1"]["description"] == "1000 GB nvme" and all(i["discovered"] is True for i in items.values())
    assert any("pve-core" in line and "reports a port enx0" in line for line in applied.review)
    assert any("pve-lab" in line and "no hardware facts read yet" in line for line in applied.review)
    # The cable to the switch is the one the host heard the switch announce.
    (cable,) = api.objects["dcim/cables"]
    assert cable["a_terminations"] == [{"object_type": "dcim.interface", "object_id": port[(core, "nic0")]["id"]}]
    assert cable["b_terminations"] == [{"object_type": "dcim.interface", "object_id": port[(switch, "8")]["id"]}]
    assert cable["tags"] == [tags["observed"]] and cable["status"] == "connected"
    moved = facts()
    moved["pve-core"]["neighbours"]["nic0"]["port_id"] = "3"
    replugged = run(True, seen=moved)
    assert len(api.objects["dcim/cables"]) == 1 and any("already has another cable" in line for line in replugged.review)
    stranger = facts()
    stranger["pve-core"]["neighbours"]["nic0"]["management_address"] = "192.168.0.250"
    assert any("not a device and port of inventory.yaml" in line for line in run(False, seen=stranger).review)

    # Guests no root defines: created once, on the right cluster and host; containers marked as such. What
    # inventory.yaml describes has a role and is not flagged; what nobody described is.
    caddy, scratch = api.get(vms, name="caddy"), api.get(vms, name="scratch")
    assert caddy["cluster"] == cluster["homelab"] and set(caddy["tags"]) == {tags["discovered"], tags["lxc"]}
    assert caddy["role"] == role["legacy-service"] and caddy["description"].startswith("Caddy") and caddy["platform"] == platform["debian"]
    assert caddy["device"] == device["pve-lab-legacy"]["id"], "the old host is not the new pve-lab"
    assert api.get(vms, name="deb13-monitoring")["status"] == "offline" and api.get(vms, name="deb13-monitoring")["platform"] == platform["debian-13"]
    assert set(scratch["tags"]) == {tags["discovered"], tags["needs-review"]} and "role" not in scratch
    assert set(api.get(vms, name="print-server")["tags"]) == {tags["discovered"], tags["lxc"], tags["needs-review"]}, "described, but still to verify"
    assert api.get(vms, name="desktop")["role"] == role["desktop"] and api.get(vms, name="desktop")["platform"] == platform["windows-11"]
    assert any("scratch" in line and "no static address" in line for line in applied.review)
    assert not any("deb13-monitoring" in line and "no static address" in line for line in applied.review), "a stopped guest is not worth a line"
    # Unverified devices are flagged, verified ones are not; the backup server is a VM on the NAS, stopped.
    assert device["pfsense"]["tags"] == [tags["needs-review"]] and device["pve-core"]["tags"] == [] and "pbs" not in device
    pbs = api.get(vms, name="pbs")
    assert (pbs["cluster"], pbs["device"], pbs["status"]) == (cluster["truenas"], device["truenas"]["id"], "offline")
    assert api.get(ips, address="192.168.0.15/24")["status"] == "reserved" and pbs["primary_ip4"] == api.get(ips, address="192.168.0.15/24")["id"]

    # A record flagged earlier loses the flag once inventory.yaml describes it; a person's own tag stays.
    api.get(vms, name="caddy")["tags"] = [tags["discovered"], tags["lxc"], tags["needs-review"], 777]
    api.get("dcim/devices", name="switch")["tags"] = [tags["needs-review"], 888]
    cleared = run(True)
    assert set(api.get(vms, name="caddy")["tags"]) == {tags["discovered"], tags["lxc"], 777}
    assert api.get("dcim/devices", name="switch")["tags"] == [888] and len(cleared.operations) == 2

    # What belongs to people survives: placement, asset tag, comments, tags, and the name of a discovered guest.
    # What Git states or a machine reports is put back.
    api.get("dcim/devices", name="pve-core").update(comments="left shelf", asset_tag="A-1", rack=55, description="edited in NetBox")
    api.get(vms, name="caddy").update(memory=1, name="caddy-renamed", comments="mine")
    api.get(vms, name="k3s-server-01")["tags"].append(12345)
    edited = run(True)
    assert len(edited.operations) == 2 and any(op.startswith("update  device pve-core: description:") for op in edited.operations)
    assert any(op.startswith("update  lxc caddy (homelab 204): memory: 1 -> 4096") for op in edited.operations)
    core_device = api.get("dcim/devices", name="pve-core")
    assert (core_device["comments"], core_device["asset_tag"], core_device["rack"]) == ("left shelf", "A-1", 55)
    assert api.get(vms, name="caddy-renamed")["comments"] == "mine" and api.get(vms, name="caddy-renamed")["memory"] == 4096
    assert any("name is 'caddy-renamed' in NetBox and 'caddy' on Proxmox" in line for line in edited.review)
    api.get(vms, name="caddy-renamed")["name"] = "caddy"

    # A rack and a place in it, stated in inventory.yaml, are written while NetBox has none; afterwards the
    # place belongs to NetBox.
    racked = copy.deepcopy(seed)
    racked["racks"] = [{"name": "rack-01", "u_height": 12, "width": 19}]
    next(d for d in racked["devices"] if d["name"] == "switch").update(rack="rack-01", position=3, face="front")
    placed = run(True, inventory=racked)
    rack = api.get("dcim/racks", name="rack-01")
    assert rack["u_height"] == 12 and any(op.startswith("update  device switch:") and "position" in op for op in placed.operations)
    assert (api.get("dcim/devices", name="switch")["rack"], api.get("dcim/devices", name="switch")["position"]) == (rack["id"], 3)
    api.get("dcim/devices", name="switch")["position"] = 7
    assert run(True, inventory=racked).operations == [] and api.get("dcim/devices", name="switch")["position"] == 7
    # A cable nobody can read from a machine is stated in inventory.yaml.
    racked["cables"] = [{"a": ["truenas", "enp1s0"], "b": ["switch", 9], "type": "dac-passive"}]
    assert run(True, inventory=racked).operations == ["create  cable truenas enp1s0 - switch 9"]
    assert sorted(c.get("type", "") for c in api.objects["dcim/cables"]) == ["", "dac-passive"] and run(False, inventory=racked).operations == []

    # Git owns the IaC fields: a rename in Git is written, and the person's tag stays.
    renamed = [dict(MACHINES[0], name="k3s-server-99"), MACHINES[1]]
    result = run(True, machines=renamed)
    assert any(op.startswith("update  vm k3s-server-99: name: 'k3s-server-01' -> 'k3s-server-99'") for op in result.operations)
    assert any("name is 'k3s-server-99' in Git and 'k3s-server-01' on Proxmox" in line for line in result.review)
    assert api.get(vms, name="k3s-server-99")["tags"] == [tags["iac"], 12345]
    run(True)  # back to the real name

    # An address held by something else is never taken; a vanished guest and an undefined IaC record are reported.
    moved = [MACHINES[0], dict(MACHINES[1], address="192.168.0.24")]
    conflict = run(False, machines=moved)
    assert any("192.168.0.24/24 is assigned to another object" in line for line in conflict.review)
    assert not any("192.168.0.24" in op for op in conflict.operations)
    gone = snapshots()
    gone["legacy"]["guests"] = gone["legacy"]["guests"][:1]
    count = len(api.objects[vms])
    vanished = run(True, machines=MACHINES[:1], observed=gone)
    assert len(api.objects[vms]) == count, "nothing is deleted"
    assert any("deb13-monitoring" in line and "no longer on Proxmox" in line for line in vanished.review)
    assert any("dns-01" in line and "no root defines it" in line for line in vanished.review)

    # An address a person entered without an owner is not handed to a discovered guest automatically.
    api.create(ips, {"address": "192.168.0.99/24", "status": "reserved", "description": "entered by hand"})
    lone = snapshots()
    lone["legacy"]["guests"].append(guest(215, "nas-proxy", "pve-lab", kind="lxc", ip="192.168.0.99/24"))
    unowned = run(True, observed=lone)
    assert any("nas-proxy" in line and "192.168.0.99/24 exists in NetBox without an owner" in line for line in unowned.review)
    assert "assigned_object_id" not in api.get(ips, address="192.168.0.99/24") and "primary_ip4" not in api.get(vms, name="nas-proxy")

    # An old snapshot may be planned from, never applied.
    stale = snapshots()
    stale["legacy"]["age_hours"] = 30
    assert any("30 h old" in line for line in run(False, observed=stale).review)
    try:
        run(True, observed=stale)
    except SystemExit:
        pass
    else:
        raise AssertionError("a stale snapshot must not be applied")

    # The picture of a role in the topology diagram: one of the plugin's own files, by role id.
    icons = sync.role_icons(seed, api)
    assert icons[str(role["hypervisor"])] == "/static/netbox_topology_views/img/server.svg" and str(role["dns"]) not in icons
    assert "icon" not in api.get("dcim/device-roles", slug="hypervisor"), "the picture is the plugin's, not a field of the role"
    assert {r["icon"] for r in seed["roles"] if "icon" in r} <= {"server", "router", "switch", "wireless-ap", "storage", "backup", "firewall"}

    # Retired records: reported by the plan, removed only by the separate command, one named record at a time.
    api.create("dcim/manufacturers", {"name": "Unknown", "slug": "unknown"})
    api.create("dcim/devices", {"name": "pbs"})
    assert any("retired record still in NetBox: dcim/devices {'name': 'pbs'}" in line for line in run(False).review)
    removed = []

    def remove(path, object_id):
        if path == "dcim/manufacturers":
            raise RuntimeError("HTTP 409 Unable to delete object. 1 dependent objects were found")
        removed.append((path, object_id))
        api.objects[path] = [item for item in api.objects[path] if item["id"] != object_id]

    lines, refused = sync.prune(seed, api, remove)
    assert [path for path, _ in removed] == ["dcim/devices"] and refused == 1, "only what inventory.yaml retires, and NetBox may refuse"
    assert any(line.startswith("removed  dcim/devices {'name': 'pbs'}") for line in lines)
    assert any(line.startswith("refused  dcim/manufacturers {'slug': 'unknown'}") for line in lines)
    assert sum(line.startswith("gone") for line in lines) == len(seed["retired"]) - 2


def allocation():
    """A root's plan is compared with NetBox before its checksum is printed: a VMID or an address of another
    machine is a conflict; without NetBox the check passes and says that it did not run."""
    plan = {"planned_values": {"root_module": {"child_modules": [{"resources": [
        {"type": "proxmox_virtual_environment_vm", "values": {"name": "k3s-server-01", "vm_id": 310, "node_name": "pve-lab",
                                                              "initialization": [{"ip_config": [{"ipv4": [{"address": "192.168.0.40/24"}]}]}]}},
        {"type": "proxmox_virtual_environment_vm", "values": {"name": "k3s-agent-01", "vm_id": 320, "node_name": "pve-core",
                                                              "initialization": [{"ip_config": [{"ipv4": [{"address": "dhcp"}]}]}]}},
        {"type": "terraform_data", "values": {"name": "not a machine"}}]}]}}}
    machines = sync.planned_machines(plan)
    assert machines == [{"name": "k3s-server-01", "vmid": 310, "node": "pve-lab", "addresses": ["192.168.0.40/24"]},
                        {"name": "k3s-agent-01", "vmid": 320, "node": "pve-core", "addresses": []}]
    api = FakeNetBox()
    assert sync.allocation(machines, api, "doku-lab") == ([], ["NetBox has no cluster doku-lab; nothing to compare with"])
    seed = yaml.safe_load((DIR / "inventory.yaml").read_text())
    sync.reconcile(seed, MACHINES, snapshots(), api, True, {})
    writes = len(api.writes)
    conflicts, notes = sync.allocation(machines, api, "doku-lab")
    assert conflicts == [] and notes == ["k3s-agent-01: VMID 320 and no fixed address are free in NetBox"]
    taken = [{"name": "k3s-agent-01", "vmid": 370, "node": "pve-core", "addresses": ["192.168.0.40/24", "192.168.0.11/24", "192.168.0.60/24"]}]
    conflicts, notes = sync.allocation(taken, api, "doku-lab")
    assert conflicts == ["k3s-agent-01: VMID 370 is dns-01 in NetBox", "k3s-agent-01: 192.168.0.40/24 belongs to k3s-server-01 in NetBox",
                         "k3s-agent-01: 192.168.0.11/24 belongs to pve-core in NetBox"]
    assert len(notes) == 1 and "192.168.0.60/24 is in NetBox without a machine (PostgreSQL primary" in notes[0]
    assert len(api.writes) == writes, "the check only reads"
    # Every root that creates VMs runs the check after saving its plan and before printing the checksum.
    make = (ROOT / "Makefile").read_text()
    for root in seed["iac_roots"]:
        (line,) = re.findall(rf"^\t\$\(call NETBOX_ALLOCATION,{re.escape(root['root'])},\$\((\w+)_PLAN\)\)$", make, re.M)
        recipe = make[make.rindex("\n\n", 0, make.index(f"$(call NETBOX_ALLOCATION,{root['root']},")):]
        assert recipe.index(f"plan -input=false -out=$({line}_PLAN)") < recipe.index("NETBOX_ALLOCATION") < recipe.index("shasum -a 256")
    macro = re.search(r"^define NETBOX_ALLOCATION\n(.*?)^endef", make, re.M | re.S).group(1)
    assert "check-plan $(1) $(2)" in macro and "exit 3" in macro and "allocation check skipped" in macro
    # Without a token nothing is asked of NetBox and nothing fails.
    import contextlib
    import io
    import os
    saved = os.environ.pop("NETBOX_READ_TOKEN", None)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sync.cmd_check_plan(seed, ["k3s", "k3s.tfplan"])
        assert "allocation check skipped: no NETBOX_READ_TOKEN" in out.getvalue()
    finally:
        if saved is not None:
            os.environ["NETBOX_READ_TOKEN"] = saved


def host_facts():
    """The script run on the hosts only reads and listens; its decoding of the switch's announcement is checked
    on a frame built here."""
    path = ROOT / "scripts/host-facts.py"
    source = path.read_text()
    assert not re.search(r"open\([^)]*['\"][wa]\+?b?['\"]|\.write_text|\.send(to)?\(|subprocess\.(run|Popen)\([^)]*shell=True|os\.(remove|unlink|system)", source)
    commands = set(re.findall(r'run\("([a-z0-9]+)"', source))
    assert commands == {"dmidecode", "lsblk", "lspci", "ethtool", "ip", "pveversion"}, commands
    spec_ = importlib.util.spec_from_file_location("host_facts", path)
    module = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(module)

    def tlv(kind, value):
        return ((kind << 9) | len(value)).to_bytes(2, "big") + value

    frame = (bytes(14) + tlv(1, b"\x04" + bytes.fromhex("245ebe000001")) + tlv(2, b"\x07" + b"8") + tlv(5, b"QSW-M3216R-8S8T")
             + tlv(8, bytes([5, 1, 192, 168, 0, 116, 2, 0, 0, 0, 1, 0])) + tlv(0, b"") + tlv(5, b"after the end"))
    assert module.decode_lldp(frame) == {"chassis_id": "24:5E:BE:00:00:01", "port_id": "8", "system_name": "QSW-M3216R-8S8T",
                                         "management_address": "192.168.0.116"}
    assert module.lldp([], 5) == {}, "nothing to listen on: returns at once"


def discovery():
    """The Proxmox client can only read; the snapshot keeps what the API says and skips templates."""
    assert [name for name in vars(sync.Proxmox) if not name.startswith("_")] == ["get"]
    assert sync.parse_nic("virtio=bc:24:11:91:6f:c6,bridge=vmbr0") == {"mac": "BC:24:11:91:6F:C6", "bridge": "vmbr0", "ip": None}
    assert sync.parse_nic("name=eth0,bridge=vmbr0,hwaddr=BC:24:11:C4:3D:9D,ip=192.168.0.24/24,gw=192.168.0.1")["ip"] == "192.168.0.24/24"
    assert sync.parse_nic("name=eth0,bridge=vmbr0,hwaddr=BC:24:11:C4:3D:9D,ip=dhcp")["ip"] is None

    class Client:
        paths = []

        def get(self, path):
            self.paths.append(path)
            if path == "/cluster/status":
                return [{"type": "cluster", "name": "doku-lab"}, {"type": "node", "name": "pve-core", "ip": "192.168.0.11", "online": 1},
                        {"type": "node", "name": "gone", "online": 0}]
            if path == "/cluster/resources?type=vm":
                return [{"vmid": 311, "name": "k3s-server-02", "node": "pve-core", "type": "qemu", "status": "running", "maxcpu": 4,
                         "maxmem": 8 * 2**30, "maxdisk": 64 * 2**30},
                        {"vmid": 9000, "name": "template", "node": "pve-core", "type": "qemu", "status": "stopped", "template": 1}]
            if path.endswith("/status"):
                return {"cpuinfo": {"model": "cpu", "cpus": 16}, "memory": {"total": 32 * 2**30}, "pveversion": "pve-manager/9"}
            if path.endswith("/network"):
                return [{"iface": "vmbr0", "type": "bridge", "cidr": "192.168.0.11/24", "bridge_ports": "nic0", "active": 1},
                        {"iface": "nic0", "type": "eth", "active": 1}, {"iface": "tap311i0", "type": "unknown"}]
            if path.endswith("/qemu/311/config"):
                return {"net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr0", "ipconfig0": "ip=192.168.0.41/24,gw=192.168.0.1", "ostype": "l26",
                        "scsi0": "local-lvm:vm-311-disk-0,iothread=1,size=64G", "scsi1": "local-lvm:vm-311-disk-1,size=512M",
                        "ide2": "local:iso/debian.iso,media=cdrom,size=700M", "efidisk0": "local-lvm:vm-311-disk-2,size=4M"}
            raise AssertionError(path)

    class Limited(Client):
        """A token without Sys.Audit: no cluster status, no node details; guests are still listed."""

        def get(self, path):
            if path == "/nodes":
                return [{"node": "pve-core", "status": "online"}]
            if path == "/cluster/status" or path.endswith(("/status", "/network")):
                raise RuntimeError("HTTP 403 Permission check failed (/, Sys.Audit)")
            return super().get(path)

    limited = sync.discover("doku-lab", {}, Limited())
    assert limited["cluster"] is None and limited["nodes"] == [{"name": "pve-core", "ip": None, "online": True, "interfaces": []}]
    assert [g["vmid"] for g in limited["guests"]] == [311]

    snapshot = sync.discover("doku-lab", {}, Client())
    assert snapshot["cluster"] == "doku-lab" and [n["name"] for n in snapshot["nodes"]] == ["gone", "pve-core"]
    assert snapshot["nodes"][1]["interfaces"] == [
        {"name": "nic0", "type": "eth", "cidr": None, "active": True, "ports": []},
        {"name": "vmbr0", "type": "bridge", "cidr": "192.168.0.11/24", "active": True, "ports": ["nic0"]}], "bridges and ports, not what a guest adds"
    (found,) = snapshot["guests"]
    assert (found["vmid"], found["memory_mb"], found["disk_mb"], found["nics"][0]["ip"]) == (311, 8192, 65536, "192.168.0.41/24")
    # Disks one by one, without the optical drive and the firmware volume; the system kind as Proxmox names it.
    assert found["ostype"] == "l26" and found["disks"] == [{"name": "scsi0", "storage": "local-lvm", "size_mb": 65536},
                                                           {"name": "scsi1", "storage": "local-lvm", "size_mb": 512}]
    assert sync.parse_disk("rootfs", "local-lvm:vm-204-disk-0,size=8G") == {"name": "rootfs", "storage": "local-lvm", "size_mb": 8192}
    assert sync.parse_disk("scsi2", "/dev/disk/by-id/ata-X,size=8T") is None and sync.parse_disk("mp0", "/mnt/data,mp=/data") is None


def export():
    """The copy for Git: one sorted file per kind, without dates, addresses of the API or counters."""
    import tempfile

    class Api:
        def list(self, path, query=None):
            if path == "dcim/devices":
                return [{"id": 2, "url": "https://x/api/dcim/devices/2/", "display": "b", "name": "b", "created": "2026", "last_updated": "2026",
                         "site": {"id": 1, "url": "https://x/1", "name": "doku-lab", "slug": "doku-lab"}, "status": {"value": "active", "label": "Active"},
                         "interface_count": 3, "comments": "", "tags": [{"id": 5, "url": "https://x/5", "slug": "iac", "name": "IaC"}],
                         "config_context": {"merged": True}},
                        {"id": 1, "url": "u", "display": "a", "name": "a", "created": "2025", "last_updated": "2026", "site": None, "status": None}]
            if path == "extras/config-contexts":
                return [{"id": 1, "url": "u", "name": "site-network", "data": {"network": {"gateway": "192.168.0.1"}}, "sites": []}]
            return []

    with tempfile.TemporaryDirectory() as tmp:
        written = sync.export(Api(), Path(tmp))
        assert written["dcim-devices.yaml"] == 2 and len(written) == len(sync.EXPORTED)
        devices = yaml.safe_load((Path(tmp) / "dcim-devices.yaml").read_text())
        assert devices == [{"id": 1, "name": "a"}, {"id": 2, "name": "b", "site": "doku-lab", "status": "active", "tags": ["iac"]}]
        contexts = yaml.safe_load((Path(tmp) / "extras-config-contexts.yaml").read_text())
        assert contexts == [{"id": 1, "name": "site-network", "data": {"network": {"gateway": "192.168.0.1"}}}]
        first = (Path(tmp) / "dcim-devices.yaml").read_text()
        sync.export(Api(), Path(tmp))
        assert (Path(tmp) / "dcim-devices.yaml").read_text() == first, "an unchanged inventory gives an unchanged file"


def documentation():
    """The inventory page: generated from what the API returns, the same text for the same inventory, without
    serial numbers, hardware addresses or the names of personal machines."""
    def related(name, **more):
        return {"id": 1, "url": "https://x/1", "display": name, "name": name, **more}

    data = {
        "dcim/devices": [{"name": "switch", "role": related("Switch"), "status": {"value": "active", "label": "Active"}, "serial": "SERIAL-1",
                          "device_type": {"id": 1, "model": "QSW-M3216R-8S8T", "slug": "q", "manufacturer": related("QNAP")},
                          "primary_ip4": {"id": 9, "address": "192.168.0.116/24"}, "rack": related("rack-01"), "position": 3.0,
                          "tags": [{"slug": "needs-review"}], "description": "Core | switch"},
                         {"name": "pve-core", "role": related("Hypervisor"), "status": {"value": "active", "label": "Active"}, "tags": [],
                          "device_type": {"id": 2, "model": "ThinkStation P350 Tiny", "manufacturer": related("Lenovo")}, "description": ""}],
        "dcim/cables": [{"a_terminations": [{"object": {"name": "nic0", "device": related("pve-core")}}],
                         "b_terminations": [{"object": {"name": "8", "device": related("switch")}}], "tags": [{"slug": "observed"}], "type": None}],
        "dcim/inventory-items": [{"device": related("pve-core"), "name": "nvme0n1", "role": related("Disk"), "part_id": "KINGSTON", "serial": "DISK-1",
                                  "description": "1000 GB nvme"}],
        "ipam/prefixes": [{"prefix": "192.168.0.0/24", "role": None, "status": {"value": "active", "label": "Active"}, "description": "LAN"},
                          {"prefix": "10.42.0.0/16", "role": related("Kubernetes"), "status": {"value": "active", "label": "Active"}, "description": "pods"}],
        "ipam/ip-ranges": [{"start_address": "192.168.0.40/24", "end_address": "192.168.0.49/24", "role": related("k3s server"), "description": "k3s"}],
        "virtualization/virtual-machines": [
            {"name": "k3s-server-01", "cluster": related("doku-lab"), "device": related("pve-lab"), "role": related("k3s server", slug="k3s-server"),
             "platform": related("Debian 13"), "vcpus": 6.0, "memory": 12288, "disk": 65536, "primary_ip4": {"id": 1, "address": "192.168.0.40/24"},
             "status": {"value": "active", "label": "Active"}, "custom_fields": {"proxmox_vmid": 310}, "tags": [{"slug": "iac"}], "description": "terraform/stacks/k3s"},
            {"name": "my-private-desktop", "cluster": related("homelab"), "device": related("pve-lab-legacy"), "role": related("Desktop", slug="desktop"),
             "status": {"value": "offline", "label": "Offline"}, "custom_fields": {"proxmox_vmid": 501}, "tags": [], "description": ""}],
        "ipam/ip-addresses": [{"address": "192.168.0.116/24", "status": {"value": "dhcp", "label": "DHCP"}, "role": None, "dns_name": "",
                               "assigned_object": {"name": "vlan1", "device": related("switch")}, "description": "switch"},
                              {"address": "192.168.0.9/24", "status": {"value": "active", "label": "Active"}, "role": None, "dns_name": "",
                               "assigned_object": None, "description": "free text"}],
        "ipam/services": [{"parent": related("k3s-server-01"), "name": "Kubernetes API", "protocol": {"value": "tcp", "label": "TCP"}, "ports": [6443], "description": ""}],
    }

    class Api:
        def list(self, path, query=None):
            return copy.deepcopy(data[path])

    text = sync.document(Api())
    assert text == sync.document(Api()) and text.endswith("\n")
    assert "| pve-core | Hypervisor | Lenovo ThinkStation P350 Tiny |" in text and text.index("| pve-core |") < text.index("| switch | Switch |"), "sorted by name"
    assert "| switch | Switch | QNAP QSW-M3216R-8S8T | 192.168.0.116/24 | rack-01 U3 | Active (to verify) | Core \\| switch |" in text
    assert "| pve-core nic0 | switch 8 |  | announced by the switch (LLDP) |" in text
    assert "| k3s-server-01 | 310 | pve-lab | k3s server | Debian 13 | 6 | 12 GB | 64 GB | 192.168.0.40/24 | Active | terraform/stacks/k3s |" in text
    assert "my-private-desktop" not in text and "1 desktop and template machines of this cluster are in NetBox and not listed here." in text
    assert "SERIAL-1" not in text and "DISK-1" not in text, "serial numbers stay in NetBox"
    assert text.index("| 192.168.0.9/24 |") < text.index("| 192.168.0.116/24 | switch vlan1 |  | DHCP | switch |"), "addresses in numeric order"
    assert text.index("| 10.42.0.0/16 | Kubernetes |") < text.index("| 192.168.0.0/24 |")
    # The committed page: both markers once, nothing a public repository should not hold.
    page = (ROOT / make_var("NETBOX_DOCS_PAGE")).read_text()
    assert page.count(sync.GENERATED[0]) == 1 and page.count(sync.GENERATED[1]) == 1 and page.startswith("---\nid: DOC-infrastructure-inventory")
    generated = page.split(sync.GENERATED[0])[1].split(sync.GENERATED[1])[0]
    assert not re.search(r"(?i)\b([0-9a-f]{2}:){5}[0-9a-f]{2}\b|serial", generated)
    assert "document $(NETBOX_DOCS_PAGE)" in (ROOT / "Makefile").read_text()


def seed_and_inventory():
    text = (DIR / "inventory.yaml").read_text()
    seed = yaml.safe_load(text)
    assert not re.search(r"(?i)(password|token|secret)\s*:", text), "NetBox holds no credentials, neither does its seed"
    assert list(seed["sources"]) == ["doku-lab", "legacy"], "the new cluster first: the roots' VMs live there"
    assert seed["sources"]["doku-lab"]["endpoint"] == "https://192.168.0.10:8006" and (ROOT / seed["sources"]["doku-lab"]["ca"]).exists()
    assert seed["sources"]["legacy"]["endpoint"] == "https://192.168.0.14:8006", "the old environment is 192.168.0.14 only"
    assert seed["sources"]["legacy"]["device_names"] == {"pve-lab": "pve-lab-legacy"}, "two hosts are named pve-lab"
    names = [d["name"] for d in seed["devices"]]
    assert len(names) == len(set(names))
    roles, platforms = {r["slug"] for r in seed["roles"]}, {p["slug"] for p in seed["platforms"]}
    types = {t["slug"]: t for t in seed["device_types"]}
    assert len(types) == len(seed["device_types"]) and not [t for t in types.values() if re.search(r"(?i)unknown", t["model"] + t["manufacturer"])]
    racks = {rack["name"] for rack in seed["racks"]}
    old = seed["sources"]["legacy"]["endpoint"].split("//")[1].split(":")[0]
    for device in seed["devices"]:
        assert device["role"] in roles and device.get("platform", "debian-13") in platforms and device["type"] in types, device["name"]
        assert types[device["type"]]["manufacturer"] != "Unidentified" or device.get("review"), f"{device['name']}: unread hardware must be flagged for review"
        assert device.get("rack") is None or device["rack"] in racks, device["name"]
        assert device.get("facts") != old, "hardware facts are never read on the old host"
        sync.device_ports(device, types[device["type"]])  # every member and parent is a port of the device
    assert {d["name"] for d in seed["devices"] if d.get("facts")} == {"pve-management", "pve-core", "pve-infra", "pve-lab"}
    assert not re.search(r"(?i)\b([0-9a-f]{2}:){5}[0-9a-f]{2}\b|serial\s*:", text), "hardware addresses and serial numbers stay out of Git"
    for cluster, notes in seed["guests"].items():
        assert cluster in {s["cluster"] for s in seed["sources"].values()}
        assert all(n["role"] in roles and n.get("platform", "debian") in platforms and ("vmid" in n) != ("vmids" in n) for n in notes)
    assert set(seed["ostypes"].values()) <= platforms and all(m["role"] in roles for m in seed["virtual_machines"])
    assert all(set(e) == {"path", "reason", "name"} or set(e) == {"path", "reason", "slug"} for e in seed["retired"])
    assert not {e.get("name") for e in seed["retired"] if e["path"] == "dcim/devices"} & set(names), "a retired device is not also declared"
    for root in seed["iac_roots"]:
        assert root["role"] in roles and root["platform"] in platforms and (ROOT / "terraform/stacks" / root["root"]).is_dir()
    for context in seed["config_contexts"]:
        assert set(context.get("roles", [])) <= roles and set(context.get("platforms", [])) <= platforms, context["name"]
        root = context["data"].get("provisioning", {}).get("opentofu_root")
        assert root is None or (ROOT / root).is_dir(), context["name"]
    assert set(seed["services"]) <= roles and all(r.get("role", "dns") in roles for r in seed["ranges"])
    assert set(seed["device_services"]) <= set(names)
    # Ansible reads the inventory with the token from the environment and verifies the certificate.
    inventory = yaml.safe_load((ROOT / "ansible/inventories/netbox.yml").read_text())
    assert inventory["plugin"] == "netbox.netbox.nb_inventory" and inventory["api_endpoint"] == f"https://{HOST}"
    assert "token" not in inventory and inventory["validate_certs"] is True
    assert {"tag": "iac"} in inventory["vm_query_filters"], "only machines Git defines are configured through this inventory"
    assert set(inventory["groups"]) == {r["group"] for r in seed["iac_roots"]}, "the group names the playbooks already use"
    pinned = {c["name"]: c["version"] for c in yaml.safe_load((ROOT / "collections/requirements.yml").read_text())["collections"]}
    assert pinned["netbox.netbox"] == "3.24.0"


def main():
    chart()
    access()
    sso_pipeline()
    make_guards()
    reconciliation()
    allocation()
    host_facts()
    discovery()
    export()
    documentation()
    seed_and_inventory()
    print("PASS: chart pinned with single replicas, shared PostgreSQL, pinned Valkey, no secret in Git, LAN-only route; "
          "diagram plugins pinned by checksum and installed on a volume; reconciliation idempotent, never deletes, never overwrites what people entered, never prints serial numbers or "
          "hardware addresses; hosts report their hardware and switch port; discovery read-only")


if __name__ == "__main__":
    main()
