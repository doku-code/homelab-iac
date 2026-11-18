#!/usr/bin/env python3
"""NetBox inventory reconciliation (M013, ADR-016).

  scripts/netbox-sync.py discover <source>   read-only snapshot of one Proxmox environment into .local/netbox/
  scripts/netbox-sync.py plan                what would change in NetBox, and what needs a human decision
  scripts/netbox-sync.py apply               write those changes
  scripts/netbox-sync.py identities          create the two service accounts and store their API tokens
  scripts/netbox-sync.py export <directory>  write the whole inventory as sorted YAML files (for a history in Git)

Three kinds of data, never mixed (services/netbox/inventory.yaml describes the ownership):
  intended   the VMs of the OpenTofu roots (`tofu output`) and the foundation in inventory.yaml: written to NetBox
  observed   what a Proxmox API reports (snapshot): fills the sizing of known VMs, creates unknown guests once
             as "discovered, needs-review", and is otherwise only compared and reported
  NetBox     everything a person entered or validated there: never overwritten outside the fields Git owns

The script creates and updates; it never deletes. Credentials come from the environment only:
PROXMOX_VE_API_TOKEN (discover), NETBOX_SYNC_TOKEN (plan, apply), NETBOX_SUPERUSER_PASSWORD (identities).
"""
import datetime
import ipaddress
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "services/netbox/inventory.yaml"
SNAPSHOTS = ROOT / ".local/netbox"
NETBOX_URL = os.environ.get("NETBOX_URL", "https://netbox.doku-lab.net")
SNAPSHOT_MAX_AGE_HOURS = 24
TAGS = {
    "iac": ("IaC", "4caf50", "Defined in Git (OpenTofu roots); the reconciliation overwrites the fields Git owns"),
    "discovered": ("Discovered", "ff9800", "Found on a Proxmox host, not defined in Git; created once, then only compared"),
    "needs-review": ("Needs review", "f44336", "Not verified by a person yet; remove this tag once the record is validated"),
    "lxc": ("LXC", "9e9e9e", "Proxmox container (not a virtual machine)"),
}
# What the write account may touch (view, add, change; never delete) and what the read account may see.
SYNC_MODELS = ["dcim.site", "dcim.manufacturer", "dcim.devicetype", "dcim.devicerole", "dcim.platform", "dcim.device",
               "dcim.interface", "virtualization.clustertype", "virtualization.cluster", "virtualization.virtualmachine",
               "virtualization.vminterface", "ipam.prefix", "ipam.iprange", "ipam.ipaddress", "ipam.role",
               "ipam.service", "extras.tag", "extras.customfield", "extras.configcontext"]
READ_APPS = ("dcim", "ipam", "virtualization", "tenancy", "extras")


def die(message):
    print(f"netbox-sync: {message}", file=sys.stderr)
    sys.exit(2)


# ───────────────────────── HTTP ─────────────────────────

def http(method, url, headers, body=None, context=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers={"Accept": "application/json", **headers})
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            text = response.read().decode()
    except urllib.error.HTTPError as error:
        # The body explains validation errors; it holds field names and messages, not credentials.
        raise RuntimeError(f"{method} {url.split('?')[0]}: HTTP {error.code} {error.read().decode()[:400]}") from None
    return json.loads(text) if text else None


class NetBox:
    """The few REST calls the reconciliation needs. No delete method exists on purpose."""

    def __init__(self, url, token):
        self.url = url.rstrip("/")
        scheme = "Bearer" if token.startswith("nbt_") else "Token"
        self.headers = {"Authorization": f"{scheme} {token}"}

    def list(self, path, query=None):
        url = f"{self.url}/api/{path}/?{urllib.parse.urlencode({**(query or {}), 'limit': 1000})}"
        results = []
        while url:
            page = http("GET", url, self.headers)
            results += page["results"]
            url = page.get("next")
        return results

    def create(self, path, body):
        return http("POST", f"{self.url}/api/{path}/", self.headers, body)

    def update(self, path, object_id, body):
        return http("PATCH", f"{self.url}/api/{path}/{object_id}/", self.headers, body)


class Proxmox:
    """Read-only client: it can only send GET requests."""

    def __init__(self, source, token):
        self.base = source["endpoint"].rstrip("/") + "/api2/json"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        if source.get("insecure"):
            self.context = ssl._create_unverified_context()  # noqa: S323 - the old host has a self-signed certificate
        else:
            self.context = ssl.create_default_context(cafile=str(ROOT / source["ca"]))
            # Proxmox node certificates name the host; the endpoint is an IP address listed in the certificate.

    def get(self, path):
        return http("GET", self.base + path, self.headers, context=self.context)["data"]


# ───────────────────────── discovery (observed state) ─────────────────────────

def parse_nic(value):
    """'virtio=BC:24:..,bridge=vmbr0' or 'name=eth0,bridge=vmbr0,hwaddr=..,ip=192.168.0.24/24' -> mac, bridge, ip."""
    parts = dict(item.split("=", 1) for item in value.split(",") if "=" in item)
    mac = parts.get("hwaddr") or next((v for k, v in parts.items() if re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", v)), None)
    ip = parts.get("ip") if re.fullmatch(r"\d+\.\d+\.\d+\.\d+/\d+", parts.get("ip", "")) else None
    return {"mac": mac.upper() if mac else None, "bridge": parts.get("bridge"), "ip": ip}


def discover(source_name, source, client):
    # Cluster and node details need Sys.Audit, which a provisioning token may not have: they are optional.
    try:
        status = client.get("/cluster/status")
        cluster = next((item["name"] for item in status if item["type"] == "cluster"), None)
        listed = [{"name": i["name"], "ip": i.get("ip"), "online": bool(i.get("online"))} for i in status if i["type"] == "node"]
    except RuntimeError:
        cluster = None
        listed = [{"name": i["node"], "ip": None, "online": i.get("status") == "online"} for i in client.get("/nodes")]
    nodes = []
    for node in sorted(listed, key=lambda n: n["name"]):
        node["interfaces"] = []
        if node["online"]:
            try:
                info = client.get(f"/nodes/{node['name']}/status")
                node.update(cpu_model=info["cpuinfo"]["model"], cores=info["cpuinfo"]["cpus"],
                            memory_mb=info["memory"]["total"] // 2**20, version=info.get("pveversion"))
                node["interfaces"] = [{"name": n["iface"], "type": n["type"], "cidr": n["cidr"]}
                                      for n in client.get(f"/nodes/{node['name']}/network") if n.get("cidr")]
            except RuntimeError:
                pass
        nodes.append(node)
    guests = []
    for item in sorted(client.get("/cluster/resources?type=vm"), key=lambda i: i["vmid"]):
        if item.get("template"):
            continue  # images, not machines
        guest = {"vmid": item["vmid"], "name": item.get("name"), "node": item["node"], "type": item["type"],
                 "status": item["status"], "vcpus": item.get("maxcpu"), "memory_mb": item.get("maxmem", 0) // 2**20,
                 "disk_mb": item.get("maxdisk", 0) // 2**20, "nics": []}
        try:
            config = client.get(f"/nodes/{item['node']}/{item['type']}/{item['vmid']}/config")
        except RuntimeError:
            config = {}  # node offline or not readable with this token: sizing stays, addresses stay unknown
        for key in sorted(k for k in config if re.fullmatch(r"net\d+", k)):
            nic = {"name": key, **parse_nic(config[key])}
            static = parse_nic(config.get("ipconfig" + key[3:], "")).get("ip")
            nic["ip"] = nic["ip"] or static
            guest["nics"].append(nic)
        guests.append(guest)
    return {"source": source_name, "taken": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "cluster": cluster, "nodes": nodes, "guests": guests}


def cmd_discover(seed, args):
    if len(args) != 1 or args[0] not in seed["sources"]:
        die(f"usage: netbox-sync.py discover <{'|'.join(seed['sources'])}>")
    token = os.environ.get("PROXMOX_VE_API_TOKEN") or die("set PROXMOX_VE_API_TOKEN in the environment (read access is enough)")
    source = seed["sources"][args[0]]
    snapshot = discover(args[0], source, Proxmox(source, token))
    if snapshot["cluster"] is None:
        print(f"{args[0]}: this token may not read the cluster name; assuming {source['cluster']!r} from inventory.yaml")
        snapshot["cluster"] = source["cluster"]
    elif snapshot["cluster"] != source["cluster"]:
        die(f"{args[0]}: the API reports cluster {snapshot['cluster']!r}, inventory.yaml expects {source['cluster']!r}")
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    target = SNAPSHOTS / f"observed-{args[0]}.json"
    target.write_text(json.dumps(snapshot, indent=1) + "\n")
    print(f"{args[0]}: cluster {snapshot['cluster']}, {len(snapshot['nodes'])} node(s), {len(snapshot['guests'])} guest(s) "
          f"-> {target.relative_to(ROOT)}")


def load_snapshots(seed):
    snapshots, notes = {}, []
    for name in seed["sources"]:
        path = SNAPSHOTS / f"observed-{name}.json"
        if not path.exists():
            notes.append(f"no snapshot of {name}: run `make netbox-discover NETBOX_SOURCE={name}` (its guests are skipped)")
            continue
        snapshot = json.loads(path.read_text())
        age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(snapshot["taken"])
        snapshot["age_hours"] = age.total_seconds() / 3600
        snapshots[name] = snapshot
    return snapshots, notes


# ───────────────────────── intended state from the OpenTofu roots ─────────────────────────

def load_iac(seed):
    """VMs as the roots define them: {name, vmid, node, address, role, platform, root} from `tofu output`."""
    tofu = os.environ.get("TOFU", "tofu")
    machines = []
    for entry in seed["iac_roots"]:
        result = subprocess.run([tofu, f"-chdir={ROOT / 'terraform/stacks' / entry['root']}", "output", "-json", "ansible_inventory"],
                                capture_output=True, text=True)
        if result.returncode != 0:
            die(f"root {entry['root']}: `tofu output` failed (the state lives on the operator workstation only)")
        hosts = json.loads(result.stdout)["all"]["children"][entry["group"]]["hosts"]
        for name, host in sorted(hosts.items()):
            machines.append({"name": name, "vmid": host["vm_id"], "node": host.get("proxmox_node") or entry["node"],
                             "address": host["ansible_host"], "role": entry["role"], "platform": entry["platform"],
                             "root": entry["root"]})
    return machines


# ───────────────────────── reconciliation ─────────────────────────

class Pending:
    """An object the plan would create: it has no id yet."""

    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return f"(new) {self.label}"


def ref(value):
    return value if isinstance(value, Pending) else value["id"]


def norm(value):
    """Reduce an API value to something comparable with what the script sends."""
    if isinstance(value, dict):
        return value["id"] if "id" in value else value.get("value")
    if isinstance(value, list):
        return sorted(norm(item) for item in value)
    return value


def differs(existing, desired, key):
    if key == "tags":  # required tags must be present; other tags belong to people
        return not set(desired) <= set(norm(existing or []))
    if key == "custom_fields":
        return any((existing or {}).get(name) != value for name, value in desired.items())
    if key == "data":  # configuration context: free-form JSON, compared as it is
        return existing != desired
    current = norm(existing)
    if isinstance(desired, (int, float)) and not isinstance(desired, bool) and current is not None:
        try:
            return float(current) != float(desired)
        except (TypeError, ValueError):
            return True
    return current != desired


class Reconciler:
    def __init__(self, api, apply):
        self.api, self.apply = api, apply
        self.operations, self.review = [], []
        self.planned, self.claims = {}, {}

    def find(self, path, query):
        if any(isinstance(value, Pending) for value in query.values()):
            return None
        found = self.api.list(path, query)
        if len(found) > 1:
            die(f"{path} {query}: {len(found)} objects match; remove the duplicate in NetBox first")
        return found[0] if found else None

    def ensure(self, label, path, query, fields, update=True):
        """Create the object when missing. update=True: Git owns `fields`; update=False: created once, then NetBox's."""
        key = (path, tuple(sorted(query.items(), key=str)))
        if key in self.planned:  # asked for twice in one plan (a manufacturer shared by two devices)
            return self.planned[key]
        existing = self.find(path, query)
        if existing is None:
            self.operations.append(f"create  {label}")
            if not self.apply:
                self.planned[key] = Pending(label)
                return self.planned[key]
            if any(isinstance(value, Pending) for value in fields.values()):
                die(f"{label}: depends on an object that could not be created")
            return self.api.create(path, fields)
        if not update:
            return existing
        changes = {key: value for key, value in fields.items() if not isinstance(value, Pending) and differs(existing.get(key), value, key)}
        if "tags" in changes:
            changes["tags"] = sorted(set(norm(existing.get("tags") or [])) | set(changes["tags"]))
        if changes:
            shown = ", ".join(f"{key}: {norm(existing.get(key))!r} -> {value!r}" for key, value in sorted(changes.items()))
            self.operations.append(f"update  {label}: {shown}")
            if self.apply:
                return self.api.update(path, existing["id"], changes)
        return existing

    def address(self, label, address, fields, owner=None, update=True):
        """An IP address, optionally bound to an interface. An address held by another object is never taken."""
        if owner is not None:
            kind, interface = owner
            fields = {**fields, "assigned_object_type": kind, "assigned_object_id": ref(interface)}
        if self.claims.setdefault(address, label) != label:
            self.review.append(f"{label}: {address} already belongs to '{self.claims[address]}'; not changed")
            return None
        existing = self.find("ipam/ip-addresses", {"address": address})
        if existing and owner is not None and existing.get("assigned_object_id") != fields["assigned_object_id"]:
            if existing.get("assigned_object_id") is not None:
                self.review.append(f"{label}: {address} is assigned to another object in NetBox "
                                   f"({existing.get('assigned_object_type')} #{existing['assigned_object_id']}); not changed")
                return None
            if not update:
                self.review.append(f"{label}: {address} exists in NetBox without an owner; assign it there if it is this machine's")
                return None
        return self.ensure(label, "ipam/ip-addresses", {"address": address}, {"address": address, "status": "active", **fields}, update)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def reconcile(seed, machines, snapshots, api, apply):
    r = Reconciler(api, apply)
    lan = ipaddress.ip_network(seed["prefixes"][0]["prefix"])

    # Schema: tags, the one custom field, site, roles, platforms, clusters, prefix, ranges.
    tags = {slug: r.ensure(f"tag {slug}", "extras/tags", {"slug": slug}, {"name": name, "slug": slug, "color": color, "description": text})
            for slug, (name, color, text) in TAGS.items()}
    tag = {slug: ref(value) for slug, value in tags.items()}

    def tagged(*slugs):
        return [tag[slug] for slug in slugs]

    r.ensure("custom field proxmox_vmid", "extras/custom-fields", {"name": "proxmox_vmid"},
             {"name": "proxmox_vmid", "label": "Proxmox VMID", "type": "integer", "object_types": ["virtualization.virtualmachine"],
              "description": "Guest ID on its Proxmox cluster; with the cluster it identifies the guest for the reconciliation"})
    site = r.ensure(f"site {seed['site']['slug']}", "dcim/sites", {"slug": seed["site"]["slug"]}, {**seed["site"], "status": "active"})
    roles = {e["slug"]: r.ensure(f"role {e['slug']}", "dcim/device-roles", {"slug": e["slug"]}, {**e, "vm_role": True}) for e in seed["roles"]}
    platforms = {e["slug"]: r.ensure(f"platform {e['slug']}", "dcim/platforms", {"slug": e["slug"]}, dict(e)) for e in seed["platforms"]}
    cluster_type = r.ensure("cluster type proxmox-ve", "virtualization/cluster-types", {"slug": "proxmox-ve"}, {"name": "Proxmox VE", "slug": "proxmox-ve"})
    clusters = {}
    for source in seed["sources"].values():
        clusters[source["cluster"]] = r.ensure(
            f"cluster {source['cluster']}", "virtualization/clusters", {"name": source["cluster"]},
            {"name": source["cluster"], "type": ref(cluster_type), "status": "active", "scope_type": "dcim.site",
             "scope_id": ref(site), "description": source["description"]})
    for entry in seed["prefixes"]:
        r.ensure(f"prefix {entry['prefix']}", "ipam/prefixes", {"prefix": entry["prefix"]},
                 {"prefix": entry["prefix"], "status": "active", "scope_type": "dcim.site", "scope_id": ref(site), "description": entry["description"]})
    for entry in seed["ranges"]:
        start, end = f"{entry['start']}/{lan.prefixlen}", f"{entry['end']}/{lan.prefixlen}"
        fields = {"start_address": start, "end_address": end, "status": "active", "description": entry["description"]}
        if entry.get("role"):  # the IPAM role carries the slug of the machine role the range is for
            role_name = next(e["name"] for e in seed["roles"] if e["slug"] == entry["role"])
            fields["role"] = ref(r.ensure(f"address role {entry['role']}", "ipam/roles", {"slug": entry["role"]},
                                          {"name": role_name, "slug": entry["role"]}))
        if entry.get("review"):
            fields["tags"] = tagged("needs-review")
        r.ensure(f"range {entry['start']}-{entry['end'].rsplit('.', 1)[1]}", "ipam/ip-ranges", {"start_address": start, "end_address": end}, fields)

    # Parameters for automation, per site, platform or role. Git owns them.
    for entry in seed.get("config_contexts", []):
        fields = {"name": entry["name"], "description": entry["description"], "is_active": True, "data": entry["data"],
                  "sites": [ref(site)] if entry.get("sites") else [],
                  "platforms": [ref(platforms[slug]) for slug in entry.get("platforms", [])],
                  "roles": [ref(roles[slug]) for slug in entry.get("roles", [])]}
        if any(isinstance(value, Pending) for values in fields.values() if isinstance(values, list) for value in values):
            r.operations.append(f"create  config context {entry['name']}")  # its site, platform or role is new too
            continue
        r.ensure(f"config context {entry['name']}", "extras/config-contexts", {"name": entry["name"]}, fields)

    # Seed: physical devices, created once.
    devices = {}
    for entry in seed["devices"]:
        manufacturer_name, model = entry.get("manufacturer", "Unknown"), entry.get("model", "Unknown")
        manufacturer = r.ensure(f"manufacturer {manufacturer_name}", "dcim/manufacturers", {"slug": slugify(manufacturer_name)},
                                {"name": manufacturer_name, "slug": slugify(manufacturer_name)}, update=False)
        type_slug = slugify(f"{manufacturer_name}-{model}")
        device_type = r.ensure(f"device type {manufacturer_name} {model}", "dcim/device-types", {"slug": type_slug},
                               {"manufacturer": ref(manufacturer), "model": model, "slug": type_slug, "u_height": 0,
                                "part_number": entry.get("part_number", "")}, update=False)
        fields = {"name": entry["name"], "device_type": ref(device_type), "role": ref(roles[entry["role"]]), "site": ref(site),
                  "status": entry.get("status", "active"), "description": entry["description"],
                  "tags": tagged("needs-review") if entry.get("review") else []}
        if entry.get("platform"):
            fields["platform"] = ref(platforms[entry["platform"]])
        if entry.get("cluster"):
            fields["cluster"] = ref(clusters[entry["cluster"]])
        device = devices[entry["name"]] = r.ensure(f"device {entry['name']}", "dcim/devices", {"name": entry["name"], "site_id": ref(site)}, fields, update=False)
        if entry.get("address"):
            interface = r.ensure(f"device {entry['name']} interface {entry['interface']}", "dcim/interfaces",
                                 {"device_id": ref(device), "name": entry["interface"]},
                                 {"device": ref(device), "name": entry["interface"], "type": "bridge"}, update=False)
            ip = r.address(f"device {entry['name']} address", entry["address"], {"description": entry["name"]}, ("dcim.interface", interface), update=False)
            if ip is not None and (isinstance(device, Pending) or not device.get("primary_ip4")):
                r.operations.append(f"update  device {entry['name']}: primary_ip4 -> {entry['address']}")
                if apply:
                    api.update("dcim/devices", device["id"], {"primary_ip4": ip["id"]})

    def node_device(source_name, node):
        name = seed["sources"][source_name].get("device_names", {}).get(node, node)
        if name not in devices:
            r.review.append(f"{source_name}: Proxmox node {node} has no device in inventory.yaml; its guests get no host")
            return None
        return devices[name]

    def machine(label, source_name, cluster, vmid, fields, update):
        fields = {**fields, "cluster": ref(clusters[cluster]), "site": ref(site), "custom_fields": {"proxmox_vmid": vmid}}
        return r.ensure(label, "virtualization/virtual-machines", {"cluster_id": ref(clusters[cluster]), "cf_proxmox_vmid": vmid}, fields, update)

    def primary(label, vm, ip, address):
        if ip is None:
            return
        if isinstance(vm, Pending) or norm(vm.get("primary_ip4")) != ref(ip):
            r.operations.append(f"update  {label}: primary_ip4 -> {address}")
            if apply:
                api.update("virtualization/virtual-machines", vm["id"], {"primary_ip4": ip["id"]})

    # Intended: the VMs of the OpenTofu roots. They live on the new cluster, the first source.
    new_source = next(iter(seed["sources"]))
    new_cluster = seed["sources"][new_source]["cluster"]
    observed = {g["vmid"]: g for g in snapshots.get(new_source, {}).get("guests", [])}
    claimed, by_name = set(), {}
    for m in machines:
        claimed.add(m["vmid"])
        label = f"vm {m['name']}"
        fields = {"name": m["name"], "status": "active", "role": ref(roles[m["role"]]), "platform": ref(platforms[m["platform"]]),
                  "tags": tagged("iac"), "description": f"terraform/stacks/{m['root']}"}
        host = node_device(new_source, m["node"])
        if host is not None:
            fields["device"] = ref(host)
        seen = observed.get(m["vmid"])
        if seen:  # sizing is what Proxmox reports; identity and addressing are what Git says
            fields.update(vcpus=seen["vcpus"], memory=seen["memory_mb"], disk=seen["disk_mb"])
            for what, git, proxmox in (("name", m["name"], seen["name"]), ("host", m["node"], seen["node"])):
                if git != proxmox:
                    r.review.append(f"{label}: {what} is {git!r} in Git and {proxmox!r} on Proxmox")
            seen_ips = {nic["ip"].split("/")[0] for nic in seen["nics"] if nic["ip"]}
            if seen_ips and m["address"] not in seen_ips:
                r.review.append(f"{label}: address is {m['address']} in Git and {sorted(seen_ips)} in the Proxmox configuration")
            if seen["status"] != "running":
                r.review.append(f"{label}: defined in Git but {seen['status']} on Proxmox")
        elif new_source in snapshots:
            r.review.append(f"{label}: defined in Git (VMID {m['vmid']}) but not found on Proxmox")
        vm = by_name[m["name"]] = machine(label, new_source, new_cluster, m["vmid"], fields, update=True)
        interface = r.ensure(f"{label} interface net0", "virtualization/interfaces", {"virtual_machine_id": ref(vm), "name": "net0"},
                             {"virtual_machine": ref(vm), "name": "net0"})
        address = f"{m['address']}/{lan.prefixlen}"
        ip = r.address(f"{label} address", address, {"tags": tagged("iac"), "description": m["name"]}, ("virtualization.vminterface", interface))
        primary(label, vm, ip, address)
        for service in seed.get("services", {}).get(m["role"], []):
            r.ensure(f"{label} service {service['name']}", "ipam/services",
                     {"virtual_machine_id": ref(vm), "name": service["name"]},
                     {"parent_object_type": "virtualization.virtualmachine", "parent_object_id": ref(vm), "name": service["name"],
                      "protocol": service["protocol"], "ports": service["ports"], "description": service.get("description", ""),
                      "tags": tagged("iac")})

    # Addresses outside the VM interfaces: iac ones follow Git, the others are seed.
    for entry in seed["addresses"]:
        fields = {key: entry[key] for key in ("status", "role", "dns_name", "description") if key in entry}
        owner = None
        if entry.get("iac"):
            fields["tags"] = tagged("iac")
        if entry.get("vm"):
            if entry["vm"] not in by_name:
                r.review.append(f"address {entry['address']}: VM {entry['vm']} is not defined by any root")
                continue
            interface = r.find("virtualization/interfaces", {"virtual_machine_id": ref(by_name[entry["vm"]]), "name": "net0"})
            owner = ("virtualization.vminterface", interface or Pending(f"{entry['vm']} net0"))
        r.address(f"address {entry['address']}", entry["address"], fields, owner, update=bool(entry.get("iac")))

    # Observed: guests no root defines are created once and flagged; afterwards differences are only reported.
    known = {}
    if not isinstance(tag["discovered"], Pending):
        for vm in api.list("virtualization/virtual-machines", {}):
            known[(norm(vm.get("cluster")), (vm.get("custom_fields") or {}).get("proxmox_vmid"))] = vm
    for source_name, snapshot in snapshots.items():
        cluster = seed["sources"][source_name]["cluster"]
        cluster_id = None if isinstance(clusters[cluster], Pending) else clusters[cluster]["id"]
        if snapshot["age_hours"] > SNAPSHOT_MAX_AGE_HOURS:
            r.review.append(f"{source_name}: the snapshot is {snapshot['age_hours']:.0f} h old; discover again before applying")
            if apply:
                die(f"{source_name}: snapshot older than {SNAPSHOT_MAX_AGE_HOURS} h; run `make netbox-discover NETBOX_SOURCE={source_name}`")
        present = set()
        for guest in snapshot["guests"]:
            present.add(guest["vmid"])
            if source_name == new_source and guest["vmid"] in claimed:
                continue
            label = f"{guest['type']} {guest['name']} ({cluster} {guest['vmid']})"
            status = "active" if guest["status"] == "running" else "offline"
            current = known.get((cluster_id, guest["vmid"]))
            if current is not None:
                for what, netbox, proxmox in (("name", current["name"], guest["name"]), ("status", norm(current["status"]), status),
                                              ("memory", current.get("memory"), guest["memory_mb"]), ("vcpus", current.get("vcpus"), guest["vcpus"])):
                    if differs(netbox, proxmox, what):
                        r.review.append(f"{label}: {what} is {netbox!r} in NetBox and {proxmox!r} on Proxmox (not changed)")
                continue
            fields = {"name": guest["name"], "status": status, "vcpus": guest["vcpus"], "memory": guest["memory_mb"],
                      "disk": guest["disk_mb"], "tags": tagged("discovered", "needs-review", *(["lxc"] if guest["type"] == "lxc" else [])),
                      "description": f"Found on Proxmox node {guest['node']} ({source_name}); not defined in Git"}
            host = node_device(source_name, guest["node"])
            if host is not None:
                fields["device"] = ref(host)
            vm = machine(label, source_name, cluster, guest["vmid"], fields, update=False)
            first = None
            for nic in guest["nics"]:
                interface = r.ensure(f"{label} interface {nic['name']}", "virtualization/interfaces",
                                     {"virtual_machine_id": ref(vm), "name": nic["name"]}, {"virtual_machine": ref(vm), "name": nic["name"]}, update=False)
                if nic["ip"] and ipaddress.ip_interface(nic["ip"]).ip in lan:
                    ip = r.address(f"{label} address", nic["ip"], {"tags": tagged("discovered"), "description": guest["name"]},
                                   ("virtualization.vminterface", interface), update=False)
                    first = first or (ip, nic["ip"])
            if first:
                primary(label, vm, *first)
            elif not guest["nics"] or not any(nic["ip"] for nic in guest["nics"]):
                r.review.append(f"{label}: no static address in the Proxmox configuration (DHCP or set inside the guest); add it in NetBox")
        # Records whose guest is gone, and IaC records no root defines any more: reported, never deleted.
        for (known_cluster, vmid), vm in known.items():
            if known_cluster != cluster_id or vmid is None:
                continue
            vm_tags = set(norm(vm.get("tags") or []))
            if vmid not in present:
                r.review.append(f"vm {vm['name']} ({cluster} {vmid}): in NetBox but no longer on Proxmox; set its status or delete it in NetBox")
            elif tag["iac"] in vm_tags and source_name == new_source and vmid not in claimed:
                r.review.append(f"vm {vm['name']} ({cluster} {vmid}): tagged iac in NetBox but no root defines it")
    return r


def report(r, notes, apply):
    for line in r.operations:
        print(line)
    creates = sum(1 for line in r.operations if line.startswith("create"))
    print(f"\n{'applied' if apply else 'plan'}: {creates} to create, {len(r.operations) - creates} to update, nothing deleted")
    for line in notes + r.review:
        print(f"review: {line}")


def cmd_reconcile(seed, apply):
    token = os.environ.get("NETBOX_SYNC_TOKEN") or die("set NETBOX_SYNC_TOKEN in the environment (store path /netbox)")
    snapshots, notes = load_snapshots(seed)
    r = reconcile(seed, load_iac(seed), snapshots, NetBox(NETBOX_URL, token), apply)
    report(r, notes, apply)


# ───────────────────────── service accounts ─────────────────────────

def token_value(created):
    """The string a client sends: v2 tokens are 'nbt_<key>.<token>' (sent as Bearer), v1 tokens are the bare key."""
    if created.get("version") == 2:
        return f"nbt_{created['key']}.{created['token']}"
    return created.get("token") or created.get("key") or die("NetBox returned no token value")


def cmd_identities(seed):
    password = os.environ.get("NETBOX_SUPERUSER_PASSWORD") or die("set NETBOX_SUPERUSER_PASSWORD in the environment (store path /netbox)")
    # The superuser has no standing API token: one that expires in ten minutes is provisioned from the password.
    expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    admin = http("POST", f"{NETBOX_URL}/api/users/tokens/provision/", {}, {
        "username": "admin", "password": password, "expires": expires, "write_enabled": True,
        "description": "netbox-sync.py identities (expires after ten minutes)"})
    api = NetBox(NETBOX_URL, token_value(admin))
    readable = sorted(f"{t['app_label']}.{t['model']}" for app in READ_APPS for t in api.list("core/object-types", {"app_label": app}))
    accounts = (("inventory-sync", "NETBOX_SYNC_TOKEN", True, SYNC_MODELS, ["view", "add", "change"]),
                ("automation-read", "NETBOX_READ_TOKEN", False, readable, ["view"]))
    lines = []
    for username, variable, write, models, actions in accounts:
        found = api.list("users/users", {"username": username})
        user = found[0] if found else api.create("users/users", {"username": username, "password": os.urandom(30).hex(), "is_active": True})
        body = {"name": username, "description": "Managed by scripts/netbox-sync.py identities", "enabled": True,
                "object_types": models, "actions": actions, "users": [user["id"]]}
        permission = api.list("users/permissions", {"name": username})
        api.update("users/permissions", permission[0]["id"], body) if permission else api.create("users/permissions", body)
        if os.environ.get(variable):
            print(f"{username}: account and permission ensured; {variable} is already in the store, no new token")
            continue
        created = api.create("users/tokens", {"user": user["id"], "write_enabled": write, "description": f"{variable} (secret store path /netbox)"})
        lines.append(f"{variable}={token_value(created)}")
        print(f"{username}: account, permission ({', '.join(actions)}) and a new token created")
    if lines:
        stored = subprocess.run([sys.executable, str(ROOT / "scripts/secrets.py"), "set", "/netbox"], input="\n".join(lines) + "\n", text=True)
        if stored.returncode != 0:
            die("the tokens were created but not stored; delete them in NetBox (Admin > API tokens) and run again")


# ───────────────────────── export (a readable copy for a history in Git) ─────────────────────────

EXPORTED = ("dcim/sites", "dcim/manufacturers", "dcim/device-types", "dcim/device-roles", "dcim/platforms", "dcim/devices",
            "dcim/interfaces", "virtualization/cluster-types", "virtualization/clusters", "virtualization/virtual-machines",
            "virtualization/interfaces", "ipam/roles", "ipam/prefixes", "ipam/ip-ranges", "ipam/ip-addresses", "ipam/services",
            "extras/tags", "extras/custom-fields", "extras/config-contexts")
VOLATILE = ("url", "display", "display_url", "created", "last_updated", "config_context", "owner")


def plain(value):
    """An API value without what changes on its own: related objects become their name, counters and dates go."""
    if isinstance(value, dict):
        if "id" in value and "url" in value:  # a related object
            return value.get("slug") or value.get("name") or value.get("address") or value.get("display")
        if set(value) == {"value", "label"}:
            return value["value"]
        return {key: plain(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def export(api, directory):
    written = {}
    for path in EXPORTED:
        records = []
        for item in sorted(api.list(path), key=lambda item: item["id"]):
            record = {key: plain(value) for key, value in sorted(item.items())
                      if key not in VOLATILE and not key.endswith("_count") and value not in (None, "", [], {})}
            if path == "extras/config-contexts":
                record["data"] = item["data"]
            records.append(record)
        target = directory / f"{path.replace('/', '-')}.yaml"
        target.write_text(yaml.safe_dump(records, sort_keys=True, allow_unicode=True, width=120))
        written[target.name] = len(records)
    return written


def cmd_export(args):
    if len(args) != 1:
        die("usage: netbox-sync.py export <directory>")
    token = os.environ.get("NETBOX_READ_TOKEN") or die("set NETBOX_READ_TOKEN in the environment (store path /netbox)")
    directory = Path(args[0])
    directory.mkdir(parents=True, exist_ok=True)
    written = export(NetBox(NETBOX_URL, token), directory)
    print(f"{sum(written.values())} records in {len(written)} files -> {directory}")


def main(argv):
    if argv and argv[0] == "export":
        return cmd_export(argv[1:])
    if not argv or argv[0] not in ("discover", "plan", "apply", "identities"):
        die("usage: netbox-sync.py discover <source> | plan | apply | identities | export <directory>")
    seed = yaml.safe_load(SEED.read_text())
    if argv[0] == "discover":
        cmd_discover(seed, argv[1:])
    elif argv[0] == "identities":
        cmd_identities(seed)
    else:
        cmd_reconcile(seed, apply=argv[0] == "apply")


if __name__ == "__main__":
    main(sys.argv[1:])
