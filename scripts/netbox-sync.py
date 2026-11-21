#!/usr/bin/env python3
"""NetBox inventory reconciliation (M013, ADR-016).

  scripts/netbox-sync.py discover <source>            read-only snapshot of one Proxmox environment into .local/netbox/
  scripts/netbox-sync.py discover-hardware [device]   hardware facts of the hosts (scripts/host-facts.py over SSH, read-only)
  scripts/netbox-sync.py plan                         what would change in NetBox, and what needs a human decision
  scripts/netbox-sync.py apply                        write those changes
  scripts/netbox-sync.py icons                        give each device role its picture in the topology diagram (plugin)
  scripts/netbox-sync.py check-plan <root> <plan>     do the VMIDs and addresses of a saved OpenTofu plan agree with NetBox?
  scripts/netbox-sync.py prune                        remove the records inventory.yaml lists under `retired`, nothing else
  scripts/netbox-sync.py identities                   create the two service accounts and store their API tokens
  scripts/netbox-sync.py export <directory>           write the whole inventory as sorted YAML files (for a history in Git)
  scripts/netbox-sync.py document <page.md>           rewrite the generated part of a documentation page from NetBox

Three kinds of data, never mixed (services/netbox/inventory.yaml describes the ownership):
  intended   the VMs of the OpenTofu roots (`tofu output`) and what inventory.yaml states (models, devices, ports,
             addresses, what the old guests are): written to NetBox
  observed   what the machines report: a Proxmox API (state, size, disks and hardware addresses of guests; unknown
             guests are created once as "discovered") and the hosts themselves (serial number, processor, memory,
             disks, hardware addresses, link speed, the switch port they are plugged into)
  NetBox     everything a person entered there (rack positions, asset tags, comments, tags, contacts): never
             overwritten outside the fields Git and the observations own

plan and apply create and update; they never delete (`prune` removes only what inventory.yaml retires).
Credentials come from the environment only: PROXMOX_VE_API_TOKEN (discover), NETBOX_SYNC_TOKEN (plan, apply),
NETBOX_SUPERUSER_PASSWORD (identities, prune).
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
    "observed": ("Observed", "03a9f4", "Recorded from what a machine reported (a cable heard through LLDP), not entered by a person"),
}
ITEM_ROLES = {"processor": ("Processor", "607d8b"), "memory": ("Memory", "3f51b5"), "disk": ("Disk", "795548")}
SOURCE_URL = "https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/"
# What the write account may touch (view, add, change; never delete) and what the read account may see.
SYNC_MODELS = ["dcim.site", "dcim.manufacturer", "dcim.devicetype", "dcim.interfacetemplate", "dcim.devicerole", "dcim.platform",
               "dcim.rack", "dcim.device", "dcim.interface", "dcim.macaddress", "dcim.cable", "dcim.inventoryitem",
               "dcim.inventoryitemrole", "virtualization.clustertype", "virtualization.cluster", "virtualization.virtualmachine",
               "virtualization.vminterface", "virtualization.virtualdisk", "ipam.prefix", "ipam.iprange", "ipam.ipaddress",
               "ipam.role", "ipam.service", "extras.tag", "extras.customfield", "extras.configcontext"]
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


DISK_KEY = re.compile(r"(scsi|virtio|sata|ide|nvme|mp)\d+|rootfs")
SIZE_MB = {"M": 1, "G": 1024, "T": 1024 * 1024}


def parse_disk(key, value):
    """'local-lvm:vm-310-disk-0,size=64G,ssd=1' -> name, storage, size in MB. Optical drives and passed-through
    paths are not disks of the guest."""
    volume, _, options = value.partition(",")
    size = re.search(r"(?:^|,)size=(\d+)([MGT])", "," + options)
    if "media=cdrom" in value or ":" not in volume or volume.startswith("/") or not size:
        return None
    return {"name": key, "storage": volume.split(":", 1)[0], "size_mb": int(size.group(1)) * SIZE_MB[size.group(2)]}


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
                # Bridges, bonds and physical ports; what Proxmox itself creates per guest is left out.
                node["interfaces"] = [{"name": n["iface"], "type": n["type"], "cidr": n.get("cidr"), "active": bool(n.get("active")),
                                       "ports": (n.get("bridge_ports") or n.get("slaves") or "").split()}
                                      for n in sorted(client.get(f"/nodes/{node['name']}/network"), key=lambda n: n["iface"])
                                      if n["type"] in ("bridge", "bond", "eth")]
            except RuntimeError:
                pass
        nodes.append(node)
    guests = []
    for item in sorted(client.get("/cluster/resources?type=vm"), key=lambda i: i["vmid"]):
        if item.get("template"):
            continue  # images, not machines
        guest = {"vmid": item["vmid"], "name": item.get("name"), "node": item["node"], "type": item["type"],
                 "status": item["status"], "vcpus": item.get("maxcpu"), "memory_mb": item.get("maxmem", 0) // 2**20,
                 "disk_mb": item.get("maxdisk", 0) // 2**20, "nics": [], "disks": [], "ostype": None}
        try:
            config = client.get(f"/nodes/{item['node']}/{item['type']}/{item['vmid']}/config")
        except RuntimeError:
            config = {}  # node offline or not readable with this token: sizing stays, addresses stay unknown
        for key in sorted(k for k in config if re.fullmatch(r"net\d+", k)):
            nic = {"name": key, **parse_nic(config[key])}
            static = parse_nic(config.get("ipconfig" + key[3:], "")).get("ip")
            nic["ip"] = nic["ip"] or static
            guest["nics"].append(nic)
        guest["ostype"] = config.get("ostype")
        guest["disks"] = [disk for key in sorted(k for k in config if DISK_KEY.fullmatch(k)) if (disk := parse_disk(key, config[key]))]
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


def empty(value):
    return value in (None, "", [], {})


def real(values):
    return [value for value in values if not isinstance(value, Pending)]


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

    def ensure(self, label, path, query, fields, update=True, fill=None, drop_tags=()):
        """Create the object when missing. `fields` are written whenever they differ (update=False: only at
        creation); `fill` only while NetBox holds nothing for them; tags are added, never removed, except the
        ones named in `drop_tags`."""
        key = (path, tuple(sorted(query.items(), key=str)))
        if key in self.planned:  # asked for twice in one plan (a manufacturer shared by two devices)
            return self.planned[key]
        existing = self.find(path, query)
        if existing is None:
            self.operations.append(f"create  {label}")
            body = {**(fill or {}), **fields}
            if not self.apply:
                self.planned[key] = Pending(label)
                return self.planned[key]
            if any(isinstance(value, Pending) for value in body.values()):
                die(f"{label}: depends on an object that could not be created")
            return self.api.create(path, body)
        changes = {}
        if update:
            changes = {name: value for name, value in fields.items()
                       if name != "tags" and not isinstance(value, Pending) and differs(existing.get(name), value, name)}
            current = set(norm(existing.get("tags") or []))
            wanted = (current | set(real(fields.get("tags", [])))) - set(real(drop_tags))
            if wanted != current:
                changes["tags"] = sorted(wanted)
        for name, value in (fill or {}).items():
            if name != "tags" and not isinstance(value, Pending) and not empty(value) and empty(norm(existing.get(name))):
                changes[name] = value
        if changes:
            # A serial number goes to NetBox only: the plan says that it changes, not to what.
            shown = ", ".join(f"{name}: changed" if name == "serial" else f"{name}: {norm(existing.get(name))!r} -> {value!r}"
                              for name, value in sorted(changes.items()))
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

    def primary(self, label, path, machine, ip, address):
        if ip is None:
            return
        if isinstance(machine, Pending) or isinstance(ip, Pending) or norm(machine.get("primary_ip4")) != ip["id"]:
            self.operations.append(f"update  {label}: primary_ip4 -> {address}")
            if self.apply:
                self.api.update(path, machine["id"], {"primary_ip4": ip["id"]})

    def hardware_address(self, label, path, filter_name, kind, interface, mac):
        """The hardware address a machine reports for one of its ports, as that port's primary one. The value is
        never printed: it goes to NetBox only."""
        if not mac:
            return
        if isinstance(interface, Pending):
            self.operations.append(f"create  {label} hardware address")
            return
        found = self.api.list("dcim/mac-addresses", {"mac_address": mac, filter_name: interface["id"]})
        if not found:
            self.operations.append(f"create  {label} hardware address")
            if not self.apply:
                return
            found = [self.api.create("dcim/mac-addresses", {"mac_address": mac, "assigned_object_type": kind, "assigned_object_id": interface["id"]})]
        elif norm(interface.get("primary_mac_address")) != found[0]["id"]:
            self.operations.append(f"update  {label}: primary hardware address")
        if self.apply and norm(interface.get("primary_mac_address")) != found[0]["id"]:
            self.api.update(path, interface["id"], {"primary_mac_address": found[0]["id"]})

    def cable(self, label, a, b, fields):
        """A cable between two device ports. A port that already has another cable is left alone and reported."""
        if isinstance(a, Pending) or isinstance(b, Pending):
            self.operations.append(f"create  {label}")
            return
        ends = [norm(self.find("dcim/interfaces", {"id": port["id"]}).get("cable")) for port in (a, b)]
        if ends[0] and ends[0] == ends[1]:
            return
        if ends[0] or ends[1]:
            self.review.append(f"{label}: one of the two ports already has another cable in NetBox; not changed")
            return
        self.operations.append(f"create  {label}")
        if self.apply:
            self.api.create("dcim/cables", {"a_terminations": [{"object_type": "dcim.interface", "object_id": a["id"]}],
                                            "b_terminations": [{"object_type": "dcim.interface", "object_id": b["id"]}],
                                            "status": "connected", **fields})


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def expand_ports(entries):
    """Ports as inventory.yaml lists them; a `range` gives one port per number."""
    ports = []
    for entry in entries or []:
        if "range" in entry:
            first, last = entry["range"]
            ports += [{**{k: v for k, v in entry.items() if k != "range"}, "name": str(number)} for number in range(first, last + 1)]
        else:
            ports.append(dict(entry))
    return ports


def device_ports(device, device_type):
    """The ports of a device: those of its type, refined and extended by its own list. Bridges and aggregates
    come first so that their members can refer to them, ports with a parent last."""
    ports = {port["name"]: port for port in expand_ports(device_type.get("ports"))}
    for port in expand_ports(device.get("ports")):
        ports[port["name"]] = {**ports.get(port["name"], {}), **port}
    for port in list(ports.values()):
        for member in port.get("members", []):
            if member not in ports:
                die(f"device {device['name']}: {port['name']} lists the member {member}, which is not a port of the device")
            ports[member] = {**ports[member], "bridge" if port["type"] == "bridge" else "lag": port["name"]}
    order = lambda port: (0 if port.get("type") in ("bridge", "lag") else 2 if port.get("parent") else 1)  # noqa: E731
    return sorted(ports.values(), key=order)


def guest_note(seed, cluster, vmid):
    """What inventory.yaml says about a guest no root defines (`guests`), or None."""
    for entry in seed.get("guests", {}).get(cluster, []):
        first, last = entry.get("vmids") or (entry["vmid"], entry["vmid"])
        if first <= vmid <= last:
            return entry
    return None


def reconcile(seed, machines, snapshots, api, apply, facts=None):
    r = Reconciler(api, apply)
    facts = facts or {}
    lan = ipaddress.ip_network(seed["prefixes"][0]["prefix"])

    # Schema: tags, custom fields, site, roles, platforms, clusters, prefixes, ranges.
    tags = {slug: r.ensure(f"tag {slug}", "extras/tags", {"slug": slug}, {"name": name, "slug": slug, "color": color, "description": text})
            for slug, (name, color, text) in TAGS.items()}
    tag = {slug: ref(value) for slug, value in tags.items()}

    def tagged(*slugs):
        return [tag[slug] for slug in slugs]

    r.ensure("custom field proxmox_vmid", "extras/custom-fields", {"name": "proxmox_vmid"},
             {"name": "proxmox_vmid", "label": "Proxmox VMID", "type": "integer", "object_types": ["virtualization.virtualmachine"],
              "description": "Guest ID on its Proxmox cluster; with the cluster it identifies the guest for the reconciliation"})
    r.ensure("custom field defined_in", "extras/custom-fields", {"name": "defined_in"},
             {"name": "defined_in", "label": "Defined in", "type": "url", "object_types": ["virtualization.virtualmachine"],
              "description": "The OpenTofu root of this repository that defines the machine"})
    site = r.ensure(f"site {seed['site']['slug']}", "dcim/sites", {"slug": seed["site"]["slug"]}, {**seed["site"], "status": "active"})
    roles = {e["slug"]: r.ensure(f"role {e['slug']}", "dcim/device-roles", {"slug": e["slug"]},
                                 {**{key: value for key, value in e.items() if key != "icon"}, "vm_role": True}) for e in seed["roles"]}
    platforms = {e["slug"]: r.ensure(f"platform {e['slug']}", "dcim/platforms", {"slug": e["slug"]}, dict(e)) for e in seed["platforms"]}
    clusters = {}

    def cluster_of(name, type_name, description):
        kind = r.ensure(f"cluster type {slugify(type_name)}", "virtualization/cluster-types", {"slug": slugify(type_name)},
                        {"name": type_name, "slug": slugify(type_name)})
        clusters[name] = r.ensure(f"cluster {name}", "virtualization/clusters", {"name": name},
                                  {"name": name, "type": ref(kind), "status": "active", "scope_type": "dcim.site",
                                   "scope_id": ref(site), "description": description})

    for source in seed["sources"].values():
        cluster_of(source["cluster"], "Proxmox VE", source["description"])
    for entry in seed.get("clusters", []):
        cluster_of(entry["name"], entry["type"], entry["description"])
    address_roles = {}

    def address_role(slug, name):
        if slug not in address_roles:
            address_roles[slug] = r.ensure(f"address role {slug}", "ipam/roles", {"slug": slug}, {"name": name, "slug": slug})
        return ref(address_roles[slug])

    for entry in seed.get("address_roles", []):
        address_role(entry["slug"], entry["name"])
    for entry in seed["prefixes"]:
        fields = {"prefix": entry["prefix"], "status": entry.get("status", "active"), "description": entry["description"]}
        if entry.get("site", True):
            fields.update(scope_type="dcim.site", scope_id=ref(site))
        if entry.get("role"):
            fields["role"] = address_role(entry["role"], entry["role"])
        r.ensure(f"prefix {entry['prefix']}", "ipam/prefixes", {"prefix": entry["prefix"]}, fields)
    for entry in seed["ranges"]:
        start, end = f"{entry['start']}/{lan.prefixlen}", f"{entry['end']}/{lan.prefixlen}"
        fields = {"start_address": start, "end_address": end, "status": "active", "description": entry["description"]}
        if entry.get("role"):  # the IPAM role carries the slug of the machine role the range is for
            fields["role"] = address_role(entry["role"], next(e["name"] for e in seed["roles"] if e["slug"] == entry["role"]))
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

    # Hardware models and their ports.
    manufacturers, device_types = {}, {}

    def manufacturer(name):
        if name not in manufacturers:
            manufacturers[name] = r.ensure(f"manufacturer {name}", "dcim/manufacturers", {"slug": slugify(name)}, {"name": name, "slug": slugify(name)})
        return manufacturers[name]

    for entry in seed["device_types"]:
        made = r.ensure(f"device type {entry['slug']}", "dcim/device-types", {"slug": entry["slug"]},
                        {"manufacturer": ref(manufacturer(entry["manufacturer"])), "model": entry["model"], "slug": entry["slug"],
                         "u_height": entry["u_height"], "is_full_depth": entry.get("is_full_depth", False),
                         "part_number": entry.get("part_number", ""), "comments": entry.get("comments", "")})
        device_types[entry["slug"]] = (entry, made)
        for port in expand_ports(entry.get("ports")):
            r.ensure(f"device type {entry['slug']} port {port['name']}", "dcim/interface-templates",
                     {"device_type_id": ref(made), "name": port["name"]},
                     {"device_type": ref(made), "name": port["name"], "type": port["type"], "mgmt_only": bool(port.get("mgmt_only")),
                      "enabled": port.get("enabled", True), "description": port.get("description", "")})
    racks = {entry["name"]: r.ensure(f"rack {entry['name']}", "dcim/racks", {"site_id": ref(site), "name": entry["name"]},
                                     {"name": entry["name"], "site": ref(site), "status": "active", "u_height": entry["u_height"],
                                      "width": entry.get("width", 19), "description": entry.get("description", "")})
             for entry in seed.get("racks", [])}
    item_roles = {slug: r.ensure(f"inventory item role {slug}", "dcim/inventory-item-roles", {"slug": slug}, {"name": name, "slug": slug, "color": color})
                  for slug, (name, color) in ITEM_ROLES.items()} if facts else {}

    # Devices: what they are comes from this file, where they are belongs to NetBox, the rest is observed.
    devices, ports, managed_at = {}, {}, {}
    for entry in seed["devices"]:
        label = f"device {entry['name']}"
        type_entry, device_type = device_types[entry["type"]]
        seen = facts.get(entry["name"])
        fields = {"name": entry["name"], "device_type": ref(device_type), "role": ref(roles[entry["role"]]), "site": ref(site),
                  "status": entry.get("status", "active"), "description": entry["description"],
                  "tags": tagged("needs-review") if entry.get("review") else []}
        if entry.get("platform"):
            fields["platform"] = ref(platforms[entry["platform"]])
        if entry.get("cluster"):
            fields["cluster"] = ref(clusters[entry["cluster"]])
        if seen and seen["system"].get("serial"):
            fields["serial"] = seen["system"]["serial"]
        fill = {}
        if entry.get("rack"):
            fill = {"rack": ref(racks[entry["rack"]]), **{key: entry[key] for key in ("position", "face") if key in entry}}
        device = devices[entry["name"]] = r.ensure(label, "dcim/devices", {"name": entry["name"], "site_id": ref(site)}, fields, fill=fill,
                                                   drop_tags=[] if entry.get("review") else tagged("needs-review"))
        heard = {port["name"]: port for port in (seen or {}).get("interfaces", [])}
        own_ports = device_ports(entry, type_entry)
        for port in own_ports:
            port_label = f"{label} port {port['name']}"
            if "type" not in port:
                die(f"{label}: the port {port['name']} has no type (it is not a port of {entry['type']})")
            fields = {"device": ref(device), "name": port["name"], "type": port["type"], "mgmt_only": bool(port.get("mgmt_only")),
                      "enabled": port.get("enabled", True), "description": port.get("description", "")}
            for relation in ("bridge", "lag", "parent"):
                if port.get(relation):
                    fields[relation] = ref(ports[(entry["name"], port[relation])])
            port_facts = heard.get(port["name"])
            if port_facts and port_facts.get("carrier") and port_facts.get("speed_mbps") and port_facts["kind"] == "physical":
                fields["speed"] = port_facts["speed_mbps"] * 1000
            interface = ports[(entry["name"], port["name"])] = r.ensure(
                port_label, "dcim/interfaces", {"device_id": ref(device), "name": port["name"]}, fields)
            if port_facts and port_facts["kind"] != "bridge":
                r.hardware_address(port_label, "dcim/interfaces", "interface_id", "dcim.interface", interface, port_facts.get("mac"))
            if port.get("address"):
                address_fields = {"description": entry["name"], "status": port.get("address_status", "active")}
                if port.get("dns_name"):
                    address_fields["dns_name"] = port["dns_name"]
                ip = r.address(f"{label} address {port['address']}", port["address"], address_fields, ("dcim.interface", interface))
                managed_at[port["address"].split("/")[0]] = entry["name"]
                if port.get("primary"):
                    r.primary(label, "dcim/devices", device, ip, port["address"])
        if seen:
            for name in sorted(set(heard) - {port["name"] for port in own_ports}):
                r.review.append(f"{label}: the host reports a port {name} that inventory.yaml does not list for {entry['type']}")
            for name in sorted({port["name"] for port in own_ports if port["type"] != "virtual"} - set(heard)):
                r.review.append(f"{label}: inventory.yaml lists a port {name} that the host does not report")
            for item in hardware_items(seen):
                item_label = f"{label} {item['name']}"
                fields = {"device": ref(device), "name": item["name"], "role": ref(item_roles[item.pop("role")]), "discovered": True, **item}
                if item.get("manufacturer"):
                    fields["manufacturer"] = ref(manufacturer(item["manufacturer"]))
                r.ensure(item_label, "dcim/inventory-items", {"device_id": ref(device), "name": item["name"]}, fields)
        elif entry.get("facts"):
            r.review.append(f"{label}: no hardware facts read yet; run `make netbox-discover-hardware`")
        for service in seed.get("device_services", {}).get(entry["name"], []):
            r.ensure(f"{label} service {service['name']}", "ipam/services", {"device_id": ref(device), "name": service["name"]},
                     {"parent_object_type": "dcim.device", "parent_object_id": ref(device), "name": service["name"],
                      "protocol": service["protocol"], "ports": service["ports"], "description": service.get("description", "")})

    # Cables: the ones a host heard the switch announce (LLDP), then the ones inventory.yaml states.
    for name, seen in sorted(facts.items()):
        for local, neighbour in sorted(seen.get("neighbours", {}).items()):
            far = managed_at.get(neighbour.get("management_address"))
            far_port = ports.get((far, neighbour.get("port_id")))
            if (name, local) not in ports or far_port is None:
                r.review.append(f"device {name}: port {local} hears {neighbour.get('system_name') or 'a neighbour'} "
                                f"(port {neighbour.get('port_id')}) which is not a device and port of inventory.yaml; no cable recorded")
                continue
            r.cable(f"cable {name} {local} - {far} {neighbour['port_id']}", ports[(name, local)], far_port,
                    {"tags": tagged("observed"), "description": f"As announced by {neighbour.get('system_name') or far} (LLDP)"})
    for entry in seed.get("cables", []):
        (a_device, a_port), (b_device, b_port) = entry["a"], entry["b"]
        for end in ((a_device, str(a_port)), (b_device, str(b_port))):
            if end not in ports:
                die(f"cables: {end[0]} has no port {end[1]} in inventory.yaml")
        r.cable(f"cable {a_device} {a_port} - {b_device} {b_port}", ports[(a_device, str(a_port))], ports[(b_device, str(b_port))],
                {key: entry[key] for key in ("type", "label", "color", "description") if key in entry})

    def node_device(source_name, node):
        name = seed["sources"][source_name].get("device_names", {}).get(node, node)
        if name not in devices:
            r.review.append(f"{source_name}: Proxmox node {node} has no device in inventory.yaml; its guests get no host")
            return None
        return devices[name]

    vms = "virtualization/virtual-machines"

    def machine(label, cluster, vmid, fields, **options):
        fields = {**fields, "cluster": ref(clusters[cluster]), "site": ref(site),
                  "custom_fields": {**fields.get("custom_fields", {}), "proxmox_vmid": vmid}}
        return r.ensure(label, vms, {"cluster_id": ref(clusters[cluster]), "cf_proxmox_vmid": vmid}, fields, **options)

    def network_port(label, vm, name, mac=None):
        interface = r.ensure(f"{label} interface {name}", "virtualization/interfaces", {"virtual_machine_id": ref(vm), "name": name},
                             {"virtual_machine": ref(vm), "name": name})
        r.hardware_address(f"{label} interface {name}", "virtualization/interfaces", "vminterface_id", "virtualization.vminterface", interface, mac)
        return interface

    def disks(label, vm, seen):
        for disk in seen.get("disks", []):
            r.ensure(f"{label} disk {disk['name']}", "virtualization/virtual-disks", {"virtual_machine_id": ref(vm), "name": disk["name"]},
                     {"virtual_machine": ref(vm), "name": disk["name"], "size": disk["size_mb"], "description": f"Proxmox storage {disk['storage']}"})

    def sizing(seen):
        """What Proxmox reports. With disks listed one by one, NetBox adds them up itself."""
        size = {"vcpus": seen["vcpus"], "memory": seen["memory_mb"]}
        if not seen.get("disks"):
            size["disk"] = seen["disk_mb"]
        return size

    # Intended: the VMs of the OpenTofu roots. They live on the new cluster, the first source.
    new_source = next(iter(seed["sources"]))
    new_cluster = seed["sources"][new_source]["cluster"]
    observed = {g["vmid"]: g for g in snapshots.get(new_source, {}).get("guests", [])}
    claimed, by_name = set(), {}
    for m in machines:
        claimed.add(m["vmid"])
        label = f"vm {m['name']}"
        fields = {"name": m["name"], "status": "active", "role": ref(roles[m["role"]]), "platform": ref(platforms[m["platform"]]),
                  "tags": tagged("iac"), "description": f"terraform/stacks/{m['root']}",
                  "custom_fields": {"defined_in": f"{SOURCE_URL}terraform/stacks/{m['root']}"}}
        host = node_device(new_source, m["node"])
        if host is not None:
            fields["device"] = ref(host)
        seen = observed.get(m["vmid"])
        if seen:  # sizing is what Proxmox reports; identity and addressing are what Git says
            fields.update(sizing(seen))
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
        vm = by_name[m["name"]] = machine(label, new_cluster, m["vmid"], fields)
        interface = network_port(label, vm, "net0", next((nic["mac"] for nic in (seen or {}).get("nics", []) if nic["name"] == "net0"), None))
        disks(label, vm, seen or {})
        address = f"{m['address']}/{lan.prefixlen}"
        ip = r.address(f"{label} address", address, {"tags": tagged("iac"), "description": m["name"]}, ("virtualization.vminterface", interface))
        r.primary(label, vms, vm, ip, address)
        for service in seed.get("services", {}).get(m["role"], []):
            r.ensure(f"{label} service {service['name']}", "ipam/services",
                     {"virtual_machine_id": ref(vm), "name": service["name"]},
                     {"parent_object_type": "virtualization.virtualmachine", "parent_object_id": ref(vm), "name": service["name"],
                      "protocol": service["protocol"], "ports": service["ports"], "description": service.get("description", ""),
                      "tags": tagged("iac")})

    # Machines on other clusters than the Proxmox ones: what inventory.yaml says is all there is to know.
    for entry in seed.get("virtual_machines", []):
        label = f"vm {entry['name']}"
        fields = {"name": entry["name"], "cluster": ref(clusters[entry["cluster"]]), "site": ref(site), "status": entry.get("status", "active"),
                  "role": ref(roles[entry["role"]]), "description": entry["description"],
                  **{key: entry[key] for key in ("vcpus", "memory") if key in entry}}
        if entry.get("platform"):
            fields["platform"] = ref(platforms[entry["platform"]])
        if entry.get("device"):
            fields["device"] = ref(devices[entry["device"]])
        vm = by_name[entry["name"]] = r.ensure(label, vms, {"cluster_id": ref(clusters[entry["cluster"]]), "name": entry["name"]}, fields)
        if entry.get("address"):
            interface = network_port(label, vm, "net0")
            ip = r.address(f"{label} address", entry["address"], {"description": entry["name"], "status": entry.get("address_status", "active")},
                           ("virtualization.vminterface", interface))
            r.primary(label, vms, vm, ip, entry["address"])

    # Addresses outside the ports above: iac ones follow Git, the others are written once.
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

    # Observed: guests no root defines are created once; afterwards Proxmox keeps deciding their state, size and
    # host, inventory.yaml what they are (when it describes them), and NetBox the rest.
    known = {}
    if not isinstance(tag["discovered"], Pending):
        for vm in api.list(vms, {}):
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
            note = guest_note(seed, cluster, guest["vmid"]) or {}
            flagged = not note or bool(note.get("review"))
            current = known.get((cluster_id, guest["vmid"]))
            if current is not None and current["name"] != guest["name"]:
                r.review.append(f"{label}: name is {current['name']!r} in NetBox and {guest['name']!r} on Proxmox (not changed)")
            fields = {"status": "active" if guest["status"] == "running" else "offline", **sizing(guest)}
            fill = {"name": guest["name"], "description": f"Found on Proxmox node {guest['node']} ({source_name}); not defined in Git",
                    "tags": tagged("discovered", *(["needs-review"] if flagged else []), *(["lxc"] if guest["type"] == "lxc" else []))}
            if note.get("role"):
                fields["role"] = ref(roles[note["role"]])
            if note.get("description"):
                fields["description"] = note["description"]
            platform = note.get("platform") or seed.get("ostypes", {}).get(guest.get("ostype"))
            if platform:
                (fields if note.get("platform") else fill)["platform"] = ref(platforms[platform])
            host = node_device(source_name, guest["node"])
            if host is not None:
                fields["device"] = ref(host)
            vm = machine(label, cluster, guest["vmid"], fields, fill=fill, drop_tags=[] if flagged else tagged("needs-review"))
            disks(label, vm, guest)
            first = None
            for nic in guest["nics"]:
                interface = network_port(label, vm, nic["name"], nic.get("mac"))
                if nic["ip"] and ipaddress.ip_interface(nic["ip"]).ip in lan:
                    ip = r.address(f"{label} address", nic["ip"], {"tags": tagged("discovered"), "description": guest["name"]},
                                   ("virtualization.vminterface", interface), update=False)
                    first = first or (ip, nic["ip"])
            if first and (isinstance(vm, Pending) or not vm.get("primary_ip4")):
                r.primary(label, vms, vm, *first)
            elif not first and guest["status"] == "running" and not any(nic["ip"] for nic in guest["nics"]):
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

    # Records this file retired and that are still there.
    for entry in seed.get("retired", []):
        query = {key: entry[key] for key in ("name", "slug") if key in entry}
        if api.list(entry["path"], query):
            r.review.append(f"retired record still in NetBox: {entry['path']} {query} ({entry['reason']}); remove it with `make netbox-prune`")
    return r


def hardware_items(seen):
    """Processor, memory modules and disks of a host as inventory items (role, name, part, serial, description)."""
    items = []
    cpu = seen.get("cpu") or {}
    if cpu.get("model"):
        items.append({"role": "processor", "name": "CPU", "part_id": cpu["model"][:50],
                      "description": f"{cpu.get('cores')} cores, {cpu.get('threads')} threads"})
    for number, module in enumerate(seen.get("memory_modules", []), 1):
        maker = module.get("manufacturer") or ""
        item = {"role": "memory", "name": f"Memory {number}", "label": (module.get("slot") or "")[:64],
                "part_id": "" if (module.get("part_number") or "Unknown") == "Unknown" else module["part_number"][:50],
                "description": " ".join(str(part) for part in (f"{module['size_mb'] // 1024} GB", module.get("type"), module.get("speed")) if part)}
        if module.get("serial") and not re.fullmatch(r"(?i)unknown|0+|none|not specified", module["serial"]):
            item["serial"] = module["serial"][:50]
        if maker and not re.fullmatch(r"(?i)unknown|0x[0-9a-f]+|not specified", maker):
            item["manufacturer"] = maker
        items.append(item)
    for disk in seen.get("disks", []):
        item = {"role": "disk", "name": disk["name"], "part_id": (disk.get("model") or "")[:50],
                "description": f"{disk['size_gb']} GB {disk.get('transport') or ''}".strip()}
        if disk.get("serial"):
            item["serial"] = disk["serial"][:50]
        items.append(item)
    return items


def load_facts(seed):
    """Hardware facts read by `discover-hardware`, per device name."""
    facts = {}
    for device in seed["devices"]:
        path = SNAPSHOTS / f"hardware-{device.get('facts')}.json"
        if device.get("facts") and path.exists():
            facts[device["name"]] = json.loads(path.read_text())
    return facts


def cmd_discover_hardware(seed, args):
    """Runs scripts/host-facts.py on every device that has `facts` (root SSH, read-only, nothing left behind)."""
    old = {urllib.parse.urlparse(source["endpoint"]).hostname for name, source in seed["sources"].items() if name != next(iter(seed["sources"]))}
    script = (ROOT / "scripts/host-facts.py").read_bytes()
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    failed = 0
    for device in seed["devices"]:
        address = device.get("facts")
        if not address or (args and device["name"] not in args):
            continue
        if address in old:
            die(f"{device['name']}: {address} is the old environment; this command never logs in to it")
        result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"root@{address}", "python3 - --lldp-seconds 35"],
                                input=script, capture_output=True, timeout=180)
        try:
            read = json.loads(result.stdout)
        except ValueError:
            failed += 1
            print(f"{device['name']}: no facts ({result.stderr.decode(errors='replace').strip()[:200]})")
            continue
        target = SNAPSHOTS / f"hardware-{address}.json"
        target.write_text(json.dumps(read, indent=1) + "\n")
        target.chmod(0o600)
        neighbours = ", ".join(f"{port} on {n.get('system_name')} port {n.get('port_id')}" for port, n in sorted(read["neighbours"].items()))
        print(f"{device['name']}: {read['system'].get('manufacturer')} {read['system'].get('version') or read['system'].get('product')}, "
              f"{len(read['interfaces'])} port(s), {len(read['disks'])} disk(s); {neighbours or 'no neighbour heard'} -> {target.relative_to(ROOT)}")
    sys.exit(1 if failed else 0)


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
    r = reconcile(seed, load_iac(seed), snapshots, NetBox(NETBOX_URL, token), apply, load_facts(seed))
    report(r, notes, apply)


# ───────────────────────── allocation check for the roots' plans ─────────────────────────

def planned_machines(plan):
    """The VMs of a saved plan (`tofu show -json`): name, VMID, host and the addresses with a prefix length."""
    def walk(module):
        for resource in module.get("resources", []):
            if resource["type"] == "proxmox_virtual_environment_vm":
                values = resource["values"]
                addresses = [ipv4.get("address") for init in values.get("initialization") or []
                             for config in init.get("ip_config") or [] for ipv4 in config.get("ipv4") or []]
                yield {"name": values.get("name"), "vmid": values.get("vm_id"), "node": values.get("node_name"),
                       "addresses": [address for address in addresses if address and "/" in address]}
        for child in module.get("child_modules", []):
            yield from walk(child)
    return list(walk(plan.get("planned_values", {}).get("root_module", {})))


def allocation(machines, api, cluster_name):
    """Compares what a plan wants with what NetBox knows: a VMID or an address that NetBox gives to another
    machine is a conflict. Read-only."""
    conflicts, notes = [], []
    vms = "virtualization/virtual-machines"
    cluster = api.list("virtualization/clusters", {"name": cluster_name})
    if not cluster:
        return conflicts, [f"NetBox has no cluster {cluster_name}; nothing to compare with"]

    def owner(ip):
        kind, object_id = norm(ip.get("assigned_object_type")), ip.get("assigned_object_id")
        path, parent, parents = {"virtualization.vminterface": ("virtualization/interfaces", "virtual_machine", vms),
                                 "dcim.interface": ("dcim/interfaces", "device", "dcim/devices")}.get(kind, (None, None, None))
        if path is None or object_id is None:
            return None
        port = api.list(path, {"id": object_id})
        machine = api.list(parents, {"id": norm(port[0][parent])}) if port else []
        return machine[0]["name"] if machine else None

    for machine in machines:
        known = False
        for holder in api.list(vms, {"cluster_id": cluster[0]["id"], "cf_proxmox_vmid": machine["vmid"]}):
            known = True
            if holder["name"] != machine["name"]:
                conflicts.append(f"{machine['name']}: VMID {machine['vmid']} is {holder['name']} in NetBox")
        for address in machine["addresses"]:
            for ip in api.list("ipam/ip-addresses", {"address": address}):
                known = True
                holder = owner(ip)
                if holder is None:
                    notes.append(f"{machine['name']}: {address} is in NetBox without a machine ({ip.get('description') or 'no description'})")
                elif holder != machine["name"]:
                    conflicts.append(f"{machine['name']}: {address} belongs to {holder} in NetBox")
        if not known:
            notes.append(f"{machine['name']}: VMID {machine['vmid']} and {', '.join(machine['addresses']) or 'no fixed address'} are free in NetBox")
    return conflicts, notes


def cmd_check_plan(seed, args):
    """Run by the roots' plan targets after the plan is saved. Never needed: without NetBox it says so and passes."""
    if len(args) != 2:
        die("usage: netbox-sync.py check-plan <root> <plan file>")
    root, plan_file = args
    token = os.environ.get("NETBOX_READ_TOKEN")
    if not token:
        print("allocation check skipped: no NETBOX_READ_TOKEN in the environment (store path /netbox)")
        return
    shown = subprocess.run([os.environ.get("TOFU", "tofu"), f"-chdir={ROOT / 'terraform/stacks' / root}", "show", "-json", Path(plan_file).name],
                           capture_output=True, text=True)
    if shown.returncode != 0:
        die(f"root {root}: `tofu show` could not read {plan_file}")
    machines = planned_machines(json.loads(shown.stdout))
    cluster = seed["sources"][next(iter(seed["sources"]))]["cluster"]
    try:
        conflicts, notes = allocation(machines, NetBox(NETBOX_URL, token), cluster)
    except (OSError, RuntimeError) as error:
        print(f"allocation check skipped: NetBox did not answer ({str(error)[:120]})")
        return
    for line in notes:
        print(f"allocation: {line}")
    for line in conflicts:
        print(f"allocation CONFLICT: {line}", file=sys.stderr)
    if conflicts:
        print("The plan uses a VMID or an address NetBox gives to another machine. Correct terraform.tfvars or the record in NetBox, "
              "then plan again.", file=sys.stderr)
        sys.exit(3)
    print(f"allocation: {len(machines)} machine(s) of the plan agree with NetBox")


# ───────────────────────── service accounts ─────────────────────────

def token_value(created):
    """The string a client sends: v2 tokens are 'nbt_<key>.<token>' (sent as Bearer), v1 tokens are the bare key."""
    if created.get("version") == 2:
        return f"nbt_{created['key']}.{created['token']}"
    return created.get("token") or created.get("key") or die("NetBox returned no token value")


def administrator(purpose):
    """The superuser has no standing API token: one that expires in ten minutes is provisioned from the password."""
    password = os.environ.get("NETBOX_SUPERUSER_PASSWORD") or die("set NETBOX_SUPERUSER_PASSWORD in the environment (store path /netbox)")
    expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    admin = http("POST", f"{NETBOX_URL}/api/users/tokens/provision/", {}, {
        "username": "admin", "password": password, "expires": expires, "write_enabled": True,
        "description": f"netbox-sync.py {purpose} (expires after ten minutes)"})
    return NetBox(NETBOX_URL, token_value(admin))


def prune(seed, api, remove):
    """Removes the records inventory.yaml lists under `retired`, and nothing else. `remove(path, id)` deletes one
    record; NetBox refuses when something still refers to it, which is reported and left as it is."""
    lines, refused = [], 0
    for entry in seed.get("retired", []):
        query = {key: entry[key] for key in ("name", "slug") if key in entry}
        if set(query) != {"name"} and set(query) != {"slug"}:
            die(f"retired: {entry} must name exactly one record by name or by slug")
        found = api.list(entry["path"], query)
        if len(found) > 1:
            die(f"retired: {entry['path']} {query} matches {len(found)} records")
        if not found:
            lines.append(f"gone     {entry['path']} {query}")
            continue
        try:
            remove(entry["path"], found[0]["id"])
            lines.append(f"removed  {entry['path']} {query} ({entry['reason']})")
        except RuntimeError as error:
            refused += 1
            lines.append(f"refused  {entry['path']} {query}: {str(error)[:300]}")
    return lines, refused


def cmd_prune(seed):
    api = administrator("prune")
    lines, refused = prune(seed, api, lambda path, object_id: http("DELETE", f"{api.url}/api/{path}/{object_id}/", api.headers))
    print("\n".join(lines) or "nothing is listed under retired")
    sys.exit(1 if refused else 0)


def role_icons(seed, api):
    """The picture each device role has in the topology diagram (plugin netbox-topology-views): role id -> file
    of the plugin's own pictures. Roles without `icon` keep the plugin's choice (a file named after the role)."""
    ids = {role["slug"]: role["id"] for role in api.list("dcim/device-roles")}
    return {str(ids[role["slug"]]): f"/static/netbox_topology_views/img/{role['icon']}.svg"
            for role in seed["roles"] if role.get("icon") and role["slug"] in ids}


def cmd_icons(seed):
    token = os.environ.get("NETBOX_SYNC_TOKEN") or die("set NETBOX_SYNC_TOKEN in the environment (store path /netbox)")
    api = NetBox(NETBOX_URL, token)
    icons = role_icons(seed, api)
    try:
        http("POST", f"{api.url}/api/plugins/netbox_topology_views/images/save/", api.headers, icons)
    except RuntimeError as error:
        die(f"the topology plugin did not take the role pictures: {str(error)[:200]}")
    print(f"topology diagram: {len(icons)} device roles have their picture")


def cmd_identities(seed):
    api = administrator("identities")
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

EXPORTED = ("dcim/sites", "dcim/manufacturers", "dcim/device-types", "dcim/interface-templates", "dcim/device-roles", "dcim/platforms",
            "dcim/racks", "dcim/devices", "dcim/interfaces", "dcim/cables", "dcim/inventory-items", "virtualization/cluster-types",
            "virtualization/clusters", "virtualization/virtual-machines", "virtualization/interfaces", "virtualization/virtual-disks",
            "ipam/roles", "ipam/prefixes", "ipam/ip-ranges", "ipam/ip-addresses", "ipam/services",
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


# ───────────────────────── the inventory as a page of the documentation ─────────────────────────

GENERATED = ("<!-- netbox:generated:start -->", "<!-- netbox:generated:end -->")
UNLISTED_ROLES = ("desktop", "template")  # personal machines: counted, not named, in a public repository


def named(value, *keys):
    """The readable part of a related object as the API nests it."""
    if isinstance(value, dict):
        return next((value[key] for key in (*keys, "name", "model", "address", "label", "display") if value.get(key)), "")
    return "" if value is None else value


def table(headers, rows):
    def cell(value):
        return str("" if value is None else value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return "\n".join(lines + ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows])


def size(megabytes):
    return "" if not megabytes else f"{megabytes / 1024:g} GB"


def document(api):
    """The inventory as Markdown: what NetBox holds, without serial numbers, hardware addresses or the names of
    personal machines. The same inventory gives the same text."""
    def end(termination):
        port = termination.get("object") or {}
        return f"{named(port.get('device'))} {port.get('name', '')}".strip()

    def tags(item):
        return {tag["slug"] for tag in item.get("tags") or []}

    def address_key(item):
        return ipaddress.ip_interface(item["address"])

    devices = sorted(api.list("dcim/devices"), key=lambda d: d["name"])
    out = ["## Devices", "", table(
        ["Device", "Role", "Model", "Address", "Rack", "Status", "Description"],
        [[d["name"], named(d.get("role")), f"{named((d.get('device_type') or {}).get('manufacturer'))} {named(d.get('device_type'), 'model')}".strip(),
          named(d.get("primary_ip4"), "address"), " ".join(str(x) for x in (named(d.get("rack")), f"U{d['position']:g}" if d.get("position") else "") if x),
          named(d.get("status"), "label") + (" (to verify)" if "needs-review" in tags(d) else ""), d.get("description", "")] for d in devices])]
    cables = sorted(([sorted(end(t) for t in c.get("a_terminations") or []), sorted(end(t) for t in c.get("b_terminations") or []), c] for c in api.list("dcim/cables")),
                    key=lambda row: (row[0], row[1]))
    out += ["", "## Cabling", "", table(["From", "To", "Cable", "Known from"],
                                         [[", ".join(a), ", ".join(b), named(c.get("type"), "label"),
                                           "announced by the switch (LLDP)" if "observed" in tags(c) else "entered"] for a, b, c in cables])
            if cables else "No cable is recorded."]
    items = sorted(api.list("dcim/inventory-items"), key=lambda i: (named(i.get("device")), named(i.get("role")), i["name"]))
    out += ["", "## Hardware of the hosts", "", table(["Device", "Part", "Kind", "Model", "Details"],
                                                      [[named(i.get("device")), i["name"], named(i.get("role")), i.get("part_id", ""), i.get("description", "")] for i in items])
            if items else "No hardware was read yet (`make netbox-discover-hardware`)."]
    out += ["", "## Networks", "", table(["Prefix", "Role", "Status", "Description"],
                                         [[x["prefix"], named(x.get("role")), named(x.get("status"), "label"), x.get("description", "")]
                                          for x in sorted(api.list("ipam/prefixes"), key=lambda x: ipaddress.ip_network(x["prefix"]))]),
            "", table(["Address range", "For", "Description"],
                      [[f"{x['start_address'].split('/')[0]} to {x['end_address'].split('/')[0]}", named(x.get("role")), x.get("description", "")]
                       for x in sorted(api.list("ipam/ip-ranges"), key=lambda x: ipaddress.ip_interface(x["start_address"]))])]
    machines = api.list("virtualization/virtual-machines")
    out += ["", "## Virtual machines and containers"]
    for cluster in sorted({named(m.get("cluster")) for m in machines}):
        mine = sorted((m for m in machines if named(m.get("cluster")) == cluster), key=lambda m: ((m.get("custom_fields") or {}).get("proxmox_vmid") or 0, m["name"]))
        listed = [m for m in mine if (m.get("role") or {}).get("slug") not in UNLISTED_ROLES]
        out += ["", f"### Cluster {cluster}", "", table(
            ["Name", "VMID", "Host", "Role", "System", "vCPU", "Memory", "Disk", "Address", "Status", "Description"],
            [[m["name"], (m.get("custom_fields") or {}).get("proxmox_vmid") or "", named(m.get("device")), named(m.get("role")), named(m.get("platform")),
              f"{m['vcpus']:g}" if m.get("vcpus") else "", size(m.get("memory")), size(m.get("disk")), named(m.get("primary_ip4"), "address"),
              named(m.get("status"), "label") + (" (to verify)" if "needs-review" in tags(m) else ""), m.get("description", "")] for m in listed])]
        if len(listed) != len(mine):
            out += ["", f"{len(mine) - len(listed)} desktop and template machines of this cluster are in NetBox and not listed here."]
    addresses = sorted(api.list("ipam/ip-addresses"), key=address_key)
    out += ["", "## Addresses", "", table(
        ["Address", "On", "Name", "Kind", "Description"],
        [[a["address"], " ".join(str(x) for x in (named((a.get("assigned_object") or {}).get("device") or (a.get("assigned_object") or {}).get("virtual_machine")),
                                                   (a.get("assigned_object") or {}).get("name", "")) if x),
          a.get("dns_name", ""), " ".join(x for x in (named(a.get("status"), "label"), named(a.get("role"), "label")) if x and x != "Active"),
          a.get("description", "")] for a in addresses])]
    services = sorted(api.list("ipam/services"), key=lambda x: (named(x.get("parent")), x["name"]))
    out += ["", "## Services", "", table(["Machine", "Service", "Protocol", "Ports", "Description"],
                                         [[named(x.get("parent")), x["name"], named(x.get("protocol"), "label"), ", ".join(str(port) for port in x.get("ports") or []),
                                           x.get("description", "")] for x in services])]
    return "\n".join(out) + "\n"


def cmd_document(args):
    """Rewrites the generated part of a page (between the two markers); the rest of the page is left as it is."""
    if len(args) != 1:
        die("usage: netbox-sync.py document <page.md>")
    token = os.environ.get("NETBOX_READ_TOKEN") or die("set NETBOX_READ_TOKEN in the environment (store path /netbox)")
    page = Path(args[0])
    text = page.read_text()
    if text.count(GENERATED[0]) != 1 or text.count(GENERATED[1]) != 1:
        die(f"{page}: the page must hold the two markers {GENERATED[0]} and {GENERATED[1]} once each")
    head, rest = text.split(GENERATED[0])
    new = head + GENERATED[0] + "\n" + document(NetBox(NETBOX_URL, token)) + GENERATED[1] + rest.split(GENERATED[1])[1]
    if new == text:
        print(f"{page}: unchanged")
        return
    today = datetime.date.today().isoformat()
    page.write_text(re.sub(r"(?m)^updated: .*$", f"updated: {today}", new, count=1))
    print(f"{page}: rewritten from NetBox")


def main(argv):
    if argv and argv[0] == "export":
        return cmd_export(argv[1:])
    if argv and argv[0] == "document":
        return cmd_document(argv[1:])
    if not argv or argv[0] not in ("discover", "discover-hardware", "plan", "apply", "icons", "prune", "identities", "check-plan"):
        die("usage: netbox-sync.py discover <source> | discover-hardware [device ...] | plan | apply | icons | prune | identities | export <directory>")
    seed = yaml.safe_load(SEED.read_text())
    if argv[0] == "discover":
        cmd_discover(seed, argv[1:])
    elif argv[0] == "discover-hardware":
        cmd_discover_hardware(seed, argv[1:])
    elif argv[0] == "prune":
        cmd_prune(seed)
    elif argv[0] == "icons":
        cmd_icons(seed)
    elif argv[0] == "check-plan":
        cmd_check_plan(seed, argv[1:])
    elif argv[0] == "identities":
        cmd_identities(seed)
    else:
        cmd_reconcile(seed, apply=argv[0] == "apply")


if __name__ == "__main__":
    main(sys.argv[1:])
