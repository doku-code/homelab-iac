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


def summarize(version, cluster_status, storages, bridges, resources, next_id):
    clustered = any(entry.get("type") == "cluster" for entry in cluster_status)
    return {
        "pve_version": version.get("version"),
        "standalone": not clustered,
        "storages": sorted((s["storage"], s.get("type"), s.get("content", ""), s.get("active"), s.get("avail"))
                           for s in storages),
        "storages_with_import": sorted(s["storage"] for s in storages if "import" in s.get("content", "").split(",")),
        "bridges": sorted(b["iface"] for b in bridges),
        "used_vmids": sorted(r["vmid"] for r in resources if "vmid" in r),
        "next_free_vmid": next_id,
    }


class Client:
    def __init__(self, endpoint, token, cafile=None):
        self.base = endpoint.rstrip("/") + "/api2/json"
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
        self.context = ssl.create_default_context(cafile=cafile)

    def get(self, path, **params):
        url = self.base + path + (("?" + urllib.parse.urlencode(params)) if params else "")
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
    try:
        report = summarize(client.get("/version"), client.get("/cluster/status"),
                           client.get(f"/nodes/{args.node}/storage"),
                           client.get(f"/nodes/{args.node}/network", type="any_bridge"),
                           client.get("/cluster/resources", type="vm"), client.get("/cluster/nextid"))
        required = required_privileges(args.node, args.image_datastore, args.disk_datastore, args.bridge)
        effective = {path: client.get("/access/permissions", path=path).get(path, {}) for path in required}
    except urllib.error.HTTPError as error:
        print(f"API request refused: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as error:
        if isinstance(error.reason, ssl.SSLError):
            print(f"TLS verification failed ({error.reason}); trust the PVE CA or use --cafile.", file=sys.stderr)
        else:
            print(f"Cannot reach the API: {error.reason}", file=sys.stderr)
        return 1
    report["missing_privileges"] = missing_privileges(required, effective)
    print(json.dumps(report, indent=2, default=str))
    return 1 if report["missing_privileges"] or not report["standalone"] else 0


if __name__ == "__main__":
    sys.exit(main())
