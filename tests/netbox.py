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
    result = subprocess.run(["helm", "template", "netbox", make_var("NETBOX_CHART"), "--version", make_var("NETBOX_CHART_VERSION"),
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
    assert settings["PLUGINS"] == [], "native models only"
    (claim,) = [d for d in docs if d["kind"] == "PersistentVolumeClaim"]
    assert claim["spec"]["storageClassName"] == "nvme-shared" and claim["spec"]["accessModes"] == ["ReadWriteMany"], \
        "web and worker share the media volume; live data on the NVMe storage outside k3s (ADR-012)"
    assert not [d for d in docs if d["kind"] in ("Ingress", "HTTPRoute")], "the route is in access.yaml"


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
    assert lan["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"]
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == "192.168.0.40"
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert {"name": "netbox"} in apps


def make_guards():
    make = (ROOT / "Makefile").read_text()
    for target, guard in (("netbox-deploy", "NETBOX_DEPLOY_APPROVED"), ("netbox-apply", "NETBOX_APPLY_APPROVED"),
                          ("netbox-identities", "NETBOX_IDENTITIES_APPROVED")):
        recipe = re.search(rf"^{target}:.*?(?=^\S)", make, re.M | re.S).group(0)
        assert f'test "$({guard})" = yes' in recipe, target
        refused = subprocess.run(["make", "-C", str(ROOT), target], capture_output=True, text=True)
        assert refused.returncode != 0 and "Approve" in refused.stderr + refused.stdout or "approve" in refused.stderr, target
    assert "NETBOX_SUPERUSER_API_TOKEN" not in make and "api_token=\\nvalkey_password" in make, "no standing superuser token"
    assert secret_keys() == {"secret_key", "api_token_peppers", "email_password", "username", "email", "password", "api_token",
                             "valkey_password", "db_password"}


class FakeNetBox:
    """Stores what is posted and filters the way the reconciliation asks. Like the real client, it cannot delete."""

    def __init__(self):
        self.objects, self.writes, self.next_id = {}, [], 1

    def list(self, path, query=None):
        def matches(item):
            for key, value in (query or {}).items():
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


def guest(vmid, name, node, kind="qemu", status="running", ip=None, memory=4096):
    return {"vmid": vmid, "name": name, "node": node, "type": kind, "status": status, "vcpus": 2, "memory_mb": memory,
            "disk_mb": 32768, "nics": [{"name": "net0", "mac": "BC:24:11:00:00:01", "bridge": "vmbr0", "ip": ip}]}


def snapshots():
    return {
        "doku-lab": {"age_hours": 0.1, "guests": [guest(310, "k3s-server-01", "pve-lab", ip="192.168.0.40/24"),
                                                   guest(370, "dns-01", "pve-infra", ip="192.168.0.70/24"),
                                                   guest(999, "scratch", "pve-core")]},
        "legacy": {"age_hours": 0.1, "guests": [guest(204, "caddy", "pve-lab", kind="lxc", ip="192.168.0.24/24"),
                                                 guest(208, "deb13-monitoring", "pve-lab", status="stopped")]},
    }


def reconciliation():
    seed = yaml.safe_load((DIR / "inventory.yaml").read_text())
    api = FakeNetBox()

    def run(apply, machines=MACHINES, observed=None):
        return sync.reconcile(seed, machines, snapshots() if observed is None else observed, api, apply)

    # A plan against an empty NetBox lists everything and writes nothing.
    plan = run(False)
    assert not api.writes and len(plan.operations) > 60 and all(op.startswith(("create", "update")) for op in plan.operations)
    assert "create  vm k3s-server-01" in plan.operations and "create  device pve-core" in plan.operations
    assert plan.operations.count("create  manufacturer Unknown") == 1, "a shared object is planned once"
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

    vms, ips = "virtualization/virtual-machines", "ipam/ip-addresses"
    tags = {t["slug"]: t["id"] for t in api.objects["extras/tags"]}
    cluster = {c["name"]: c["id"] for c in api.objects["virtualization/clusters"]}
    k3s = api.get(vms, name="k3s-server-01")
    assert k3s["custom_fields"] == {"proxmox_vmid": 310} and k3s["cluster"] == cluster["doku-lab"] and k3s["tags"] == [tags["iac"]]
    assert k3s["memory"] == 4096 and k3s["device"] == api.get("dcim/devices", name="pve-lab")["id"], "sizing observed, host from Git"
    address = api.get(ips, address="192.168.0.40/24")
    assert address["assigned_object_type"] == "virtualization.vminterface" and k3s["primary_ip4"] == address["id"]
    service = api.get(ips, address="192.168.0.20/24")
    assert service["role"] == "secondary" and service["assigned_object_id"] == api.get(
        "virtualization/interfaces", virtual_machine=api.get(vms, name="dns-01")["id"], name="net0")["id"]
    assert api.get(ips, address="192.168.0.60/24")["role"] == "vip" and "assigned_object_id" not in api.get(ips, address="192.168.0.60/24")

    # Guests no root defines: created once, flagged, on the right cluster and host; containers marked as such.
    caddy = api.get(vms, name="caddy")
    assert caddy["cluster"] == cluster["homelab"] and set(caddy["tags"]) == {tags["discovered"], tags["needs-review"], tags["lxc"]}
    assert caddy["device"] == api.get("dcim/devices", name="pve-lab-legacy")["id"], "the old host is not the new pve-lab"
    assert api.get(vms, name="deb13-monitoring")["status"] == "offline"
    assert set(api.get(vms, name="scratch")["tags"]) == {tags["discovered"], tags["needs-review"]}
    assert any("deb13-monitoring" in line and "no static address" in line for line in applied.review)
    # Unverified seed records are flagged; verified ones are not; unknown hardware is called unknown.
    assert api.get("dcim/devices", name="pfsense")["tags"] == [tags["needs-review"]] and api.get("dcim/devices", name="pve-core")["tags"] == []
    assert api.get("dcim/device-types", slug="unknown-unknown")["model"] == "Unknown"
    assert api.get("dcim/devices", name="pbs")["status"] == "offline"

    # NetBox is the authority for seed and discovered records: edits made there survive, differences are reported.
    api.get("dcim/devices", name="pve-core")["description"] = "edited in NetBox"
    api.get(vms, name="caddy")["memory"] = 1
    api.get(vms, name="caddy")["tags"] = [tags["discovered"]]  # a person validated it
    api.get(vms, name="k3s-server-01")["tags"].append(12345)   # a person's own tag on an IaC record
    writes = len(api.writes)
    edited = run(False)
    assert edited.operations == [] and len(api.writes) == writes
    assert any("caddy" in line and "memory is 1 in NetBox" in line and "not changed" in line for line in edited.review)

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
                return [{"iface": "vmbr0", "type": "bridge", "cidr": "192.168.0.11/24"}, {"iface": "nic0", "type": "eth"}]
            if path.endswith("/qemu/311/config"):
                return {"net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr0", "ipconfig0": "ip=192.168.0.41/24,gw=192.168.0.1"}
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
    assert snapshot["nodes"][1]["interfaces"] == [{"name": "vmbr0", "type": "bridge", "cidr": "192.168.0.11/24"}]
    (found,) = snapshot["guests"]
    assert (found["vmid"], found["memory_mb"], found["disk_mb"], found["nics"][0]["ip"]) == (311, 8192, 65536, "192.168.0.41/24")


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
    for device in seed["devices"]:
        assert device["role"] in roles and device.get("platform", "debian-13") in platforms, device["name"]
        assert ("model" in device) or device.get("review"), f"{device['name']}: unknown hardware must be flagged for review"
    for root in seed["iac_roots"]:
        assert root["role"] in roles and root["platform"] in platforms and (ROOT / "terraform/stacks" / root["root"]).is_dir()
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
    make_guards()
    reconciliation()
    discovery()
    seed_and_inventory()
    print("PASS: chart pinned with single replicas, shared PostgreSQL, pinned Valkey, no secret in Git, LAN-only route; "
          "reconciliation idempotent, never deletes, never overwrites NetBox-owned records; discovery read-only")


if __name__ == "__main__":
    main()
