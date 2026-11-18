"""Machine roles that can be provisioned, with the rules NetBox holds for each (read-only)."""
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


def main():
    ranges = {r["role"]["slug"]: r for r in netbox("ipam/ip-ranges") if r.get("role")}
    roles = []
    for context in netbox("extras/config-contexts"):
        rules = (context.get("data") or {}).get("provisioning")
        if not rules:
            continue
        for role in context["roles"]:
            address_range = ranges.get(role["slug"])
            roles.append({
                "role": role["slug"],
                "name": role["name"],
                "opentofu_root": rules["opentofu_root"],
                "ansible_group": rules["ansible_group"],
                "vmid_range": rules["vmid_range"],
                "proxmox_hosts": rules["proxmox_hosts"],
                "minimum": rules["minimum"],
                "address_range": f"{address_range['start_address']} - {address_range['end_address']}" if address_range else None,
            })
    return sorted(roles, key=lambda entry: entry["role"])
