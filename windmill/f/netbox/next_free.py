"""The next free address and VMID for a new machine of a role, as NetBox sees them (read-only: nothing is reserved)."""
import json
import urllib.parse
import urllib.request

import wmill

NETBOX_URL = "https://netbox.doku-lab.net"


def netbox(path: str, **query):
    """GET one NetBox API path with the workspace's read-only token; follows pagination."""
    token = wmill.get_variable("f/netbox/read_token")
    url = f"{NETBOX_URL}/api/{path}/?{urllib.parse.urlencode({**query, 'limit': 1000})}"
    results = []
    while url:
        request = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.load(response)
        if "results" not in page:
            return page
        results += page["results"]
        url = page.get("next")
    return results


def main(role: str = "k3s-server", cluster: str = "doku-lab"):
    contexts = [c for c in netbox("extras/config-contexts") if any(r["slug"] == role for r in c["roles"])]
    rules = next((c["data"]["provisioning"] for c in contexts if "provisioning" in (c.get("data") or {})), None)
    if rules is None:
        raise ValueError(f"NetBox has no provisioning rules for the role {role!r}")
    address_range = next((r for r in netbox("ipam/ip-ranges", role=role)), None)
    if address_range is None:
        raise ValueError(f"NetBox has no address range for the role {role!r}")
    # Addresses of the range that no record uses, in order. NetBox computes them; virtual IPs count as used.
    free_addresses = [a["address"] for a in netbox(f"ipam/ip-ranges/{address_range['id']}/available-ips")]
    low, high = rules["vmid_range"]
    used_vmids = {vm["custom_fields"].get("proxmox_vmid") for vm in netbox("virtualization/virtual-machines", cluster=cluster)}
    free_vmids = [vmid for vmid in range(low, high + 1) if vmid not in used_vmids]
    site = next((c["data"]["network"] for c in netbox("extras/config-contexts") if "network" in (c.get("data") or {})), {})
    return {
        "role": role,
        "cluster": cluster,
        "address": free_addresses[0] if free_addresses else None,
        "vmid": free_vmids[0] if free_vmids else None,
        "free_addresses": len(free_addresses),
        "free_vmids": len(free_vmids),
        "gateway": site.get("gateway"),
        "dns_servers": site.get("dns_servers"),
        "proxmox_hosts": rules["proxmox_hosts"],
        "minimum": rules["minimum"],
        "opentofu_root": rules["opentofu_root"],
        "note": "Read-only proposal: the address is reserved only when the machine is recorded in NetBox.",
    }
