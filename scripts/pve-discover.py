"""Read-only discovery of pve-management for the management VM allocation (GET requests only).

Usage (through `make mgmt-discover`, which applies pve-auth-guard.py first):
  pve-discover.py --endpoint https://192.168.0.10:8006/ --node pve-management \
      [--image-datastore local --disk-datastore local-lvm --bridge vmbr0] [--cafile pve-root-ca.pem]

Reports PVE version, standalone status, storages and content types, bridges, used VMIDs, the
next free VMID and the token's effective privileges against the minimum the OpenTofu root needs.
TLS is always verified (system trust store, or --cafile). The token is never printed.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

# Minimum privileges for terraform/stacks/pve-management-control, from the PVE API schema
# (apidoc permissions for qemu create/config/start, download-url, agent and task status).
VM_PRIVS = ["VM.Allocate", "VM.Audit", "VM.Config.CDROM", "VM.Config.CPU", "VM.Config.Cloudinit",
            "VM.Config.Disk", "VM.Config.HWType", "VM.Config.Memory", "VM.Config.Network",
            "VM.Config.Options", "VM.PowerMgmt", "VM.GuestAgent.Audit"]


def required_privileges(node, image_ds, disk_ds, bridge):
    required = {"/vms": VM_PRIVS, f"/nodes/{node}": ["Sys.Audit", "Sys.AccessNetwork"]}
    if image_ds:
        required[f"/storage/{image_ds}"] = ["Datastore.AllocateTemplate", "Datastore.Audit"]
    if disk_ds:
        required.setdefault(f"/storage/{disk_ds}", [])
        required[f"/storage/{disk_ds}"] = sorted(set(required[f"/storage/{disk_ds}"]) | {"Datastore.AllocateSpace", "Datastore.Audit"})
    if bridge:
        required[f"/sdn/zones/localnetwork/{bridge}"] = ["SDN.Use"]
    return required


def missing_privileges(required, effective):
    """effective: {path: {priv: 0|1}} as returned by /access/permissions?path=<path>."""
    missing = {}
    for path, privs in required.items():
        granted = {p for p, v in (effective.get(path) or {}).items() if v}
        lacking = [p for p in privs if p not in granted]
        if lacking:
            missing[path] = lacking
    return missing


def summarize(version, nodes, storages, bridges, resources, next_id):
    # /cluster/status needs Sys.Audit on "/", which the least-privilege token does not have;
    # the node list it can see is enough to tell a standalone host from a cluster member.
    node_names = sorted(n.get("node") for n in nodes)
    return {
        "pve_version": version.get("version"),
        "visible_nodes": node_names,
        "standalone": len(node_names) == 1,
        "storages": sorted((s["storage"], s.get("type"), s.get("content", ""), s.get("active"), s.get("avail"))
                           for s in storages),
        "storages_with_import": sorted(s["storage"] for s in storages if "import" in s.get("content", "").split(",")),
        "bridges": sorted(b["iface"] for b in bridges),
        "used_vmids": sorted(r["vmid"] for r in resources if "vmid" in r),
        "next_free_vmid": next_id,
    }


def capacity(status):
    """Host CPU and memory from /nodes/<node>/status (needs Sys.Audit on the node)."""
    cpu = status.get("cpuinfo") or {}
    memory = status.get("memory") or {}
    gib = 1024 ** 3
    return {
        "cpu_model": cpu.get("model"),
        "cpu_sockets": cpu.get("sockets"),
        "cpu_cores": cpu.get("cores"),
        "cpu_threads": cpu.get("cpus"),
        "memory_total_gib": round(memory.get("total", 0) / gib, 1),
        "memory_free_gib": round(memory.get("free", 0) / gib, 1),
    }


class Client:
    def __init__(self, endpoint, token, cafile=None):
        self.base = endpoint.rstrip("/") + "/api2/json"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        self.context = ssl.create_default_context(cafile=cafile)

    def get(self, api_path, **params):
        url = self.base + api_path + (("?" + urllib.parse.urlencode(params)) if params else "")
        request = urllib.request.Request(url, headers=self.headers, method="GET")
        with urllib.request.urlopen(request, context=self.context, timeout=20) as response:
            return json.load(response)["data"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--node", default="pve-management")
    parser.add_argument("--image-datastore")
    parser.add_argument("--disk-datastore")
    parser.add_argument("--bridge")
    parser.add_argument("--cafile", default=os.environ.get("PVE_CA_FILE") or None)
    args = parser.parse_args()
    client = Client(args.endpoint, os.environ["PROXMOX_VE_API_TOKEN"], args.cafile)
    refused = {}

    def read(api_path, default, **params):
        try:
            return client.get(api_path, **params)
        except urllib.error.HTTPError as error:
            refused[api_path + (f"?path={params['path']}" if "path" in params else "")] = f"HTTP {error.code} {error.reason}"
            return default

    try:
        report = summarize(read("/version", {}), read("/nodes", []),
                           read(f"/nodes/{args.node}/storage", []),
                           read(f"/nodes/{args.node}/network", [], type="any_bridge"),
                           read("/cluster/resources", [], type="vm"), read("/cluster/nextid", None))
        report["host"] = capacity(read(f"/nodes/{args.node}/status", {}))
        required = required_privileges(args.node, args.image_datastore, args.disk_datastore, args.bridge)
        effective = {path: (read("/access/permissions", {}, path=path) or {}).get(path, {}) for path in required}
    except urllib.error.URLError as error:
        if isinstance(error.reason, ssl.SSLError):
            print(f"TLS verification failed ({error.reason}); trust the PVE CA or use --cafile.", file=sys.stderr)
        else:
            print(f"Cannot reach the API: {error.reason}", file=sys.stderr)
        return 1
    report["missing_privileges"] = missing_privileges(required, effective)
    report["refused_requests"] = refused
    print(json.dumps(report, indent=2, default=str))
    return 1 if report["missing_privileges"] or refused or not report["standalone"] else 0


if __name__ == "__main__":
    sys.exit(main())
