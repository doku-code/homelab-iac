"""What NetBox holds, per role and status, and how many records still wait for a person's review (read-only)."""
import json
import urllib.parse
import urllib.request
from collections import Counter

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
    machines = netbox("virtualization/virtual-machines")
    devices = netbox("dcim/devices")

    def tags(record):
        return {tag["slug"] for tag in record["tags"]}

    return {
        "devices": len(devices),
        "virtual_machines": len(machines),
        "defined_in_git": sum("iac" in tags(m) for m in machines),
        "discovered": sum("discovered" in tags(m) for m in machines),
        "needs_review": sum("needs-review" in tags(r) for r in machines + devices),
        "by_role": dict(sorted(Counter((m["role"] or {}).get("slug", "none") for m in machines).items())),
        "by_status": dict(sorted(Counter(m["status"]["value"] for m in machines).items())),
        "by_host": dict(sorted(Counter((m["device"] or {}).get("name", "none") for m in machines).items())),
    }
