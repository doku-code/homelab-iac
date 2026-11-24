#!/usr/bin/env python3
"""LAN DNS (TASK-022): AdGuard Home role, its configuration from Git and the Make guards. Offline."""
import json
import os
import subprocess
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/adguard_home"
HASH = "$2a$10$" + "a" * 53  # synthetic bcrypt shape, not a real login


def render(name, **extra):
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True)
    env.filters["to_json"] = json.dumps
    values = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    values.update(yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text()))
    values.update({"adguard_admin_hash": HASH, "ansible_facts": {"default_ipv4": {"interface": "eth0"}}}, **extra)
    return env.from_string((ROLE / "templates" / name).read_text()).render(**values)


def main():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert defaults["adguard_version"].startswith("v0.107.") and len(defaults["adguard_sha256"]) == 64
    assert "lookup('ansible.builtin.env', 'ADGUARD_ADMIN_HASH')" in defaults["adguard_admin_hash"], "the hash is never in Git"
    assert defaults["adguard_service_address"] == "", "the LAN address is taken only at the cutover"

    content = yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())
    assert [f["name"] for f in content["adguard_filters"]] == ["AdGuard DNS filter", "AdAway Default Blocklist", "OISD Big"]
    rewrites = {r["domain"]: r["answer"] for r in content["adguard_rewrites"]}
    assert len(rewrites) == len(content["adguard_rewrites"]) >= 17, "one answer per name"
    assert rewrites["adguard.doku-lab.net"] == "192.168.0.20"
    # The router and the switch are reached through the ingress (valid certificate), like every other name.
    assert rewrites["pfsense.doku-lab.net"] == rewrites["switch.doku-lab.net"] == rewrites["pve-compute.doku-lab.net"] == "192.168.0.40"
    assert "git.doku-lab.net" in rewrites and "secrets.doku-lab.net" not in rewrites, "Infisical is shut down"

    config = yaml.safe_load(render("AdGuardHome.yaml.j2"))
    assert config["schema_version"] == 34 and config["users"] == [{"name": "nith", "password": HASH}]
    assert config["dns"]["upstream_dns"] == ["https://dns10.quad9.net/dns-query", "https://cloudflare-dns.com/dns-query"]
    assert config["dns"]["enable_dnssec"] is True
    assert config["dns"]["ratelimit"] == 0, "the default limit is shared by the whole /24 and drops normal browsing"
    # An internet dropout must not freeze resolution: parallel upstreams, plain fallback, short timeout, stale cache.
    assert config["dns"]["upstream_mode"] == "parallel" and config["dns"]["fallback_dns"] == ["9.9.9.10", "1.1.1.1"]
    assert config["dns"]["upstream_timeout"] == "3s" and config["dns"]["cache_optimistic"] is True
    assert config["dns"]["use_private_ptr_resolvers"] is False, "reverse lookups of LAN addresses never go to the internet"
    assert [f["id"] for f in config["filters"]] == [1, 2, 3] and all(f["enabled"] for f in config["filters"])
    assert {r["domain"]: r["answer"] for r in config["filtering"]["rewrites"]} == rewrites
    assert config["filtering"]["protection_enabled"] and config["dhcp"]["enabled"] is False

    firewall = render("firewall.nft.j2")
    assert "ip saddr { 192.168.0.0/24 } meta l4proto { tcp, udp } th dport 53 accept" in firewall
    assert "th dport 53 drop" in firewall and "tcp dport 80 drop" in firewall
    unit = render("adguardhome.service.j2")
    assert "User=adguard" in unit and "CapabilityBoundingSet=CAP_NET_BIND_SERVICE" in unit and "NoNewPrivileges=true" in unit
    address = render("dns-service-address.service.j2", adguard_service_address="192.168.0.20")
    assert "ip address replace 192.168.0.20/24 dev eth0" in address and "arping -U" in address

    tasks = {t["name"]: t for t in yaml.safe_load((ROLE / "tasks/main.yml").read_text())}
    for name in ("Require Debian 13 and the admin password hash from the environment", "Render the configuration from Git"):
        assert tasks[name].get("no_log") is True, name
    assert tasks["Download the pinned AdGuard Home release, verified by SHA256"]["ansible.builtin.get_url"]["checksum"] == "sha256:{{ adguard_sha256 }}"
    assert tasks["Render the configuration from Git"]["ansible.builtin.template"]["dest"] == "/etc/adguardhome/desired.yaml", \
        "the live file is replaced only while the service is stopped"
    handlers = yaml.safe_load((ROLE / "handlers/main.yml").read_text())
    assert [h["name"] for h in handlers if h.get("listen") == "Apply AdGuard configuration"] == [
        "Stop AdGuard Home before replacing its configuration", "Put the configuration from Git in place", "Start AdGuard Home"]

    def make(*args, env=None):
        return subprocess.run(["make", "-n", *args], cwd=ROOT, capture_output=True, text=True,
                              env={k: v for k, v in {**os.environ, **(env or {})}.items() if k != "ADGUARD_ADMIN_HASH" or env})
    assert subprocess.run(["make", "dns-configure"], cwd=ROOT, capture_output=True, text=True).returncode != 0
    refused = subprocess.run(["make", "dns-configure", "DNS_CONFIGURE_APPROVED=yes"], cwd=ROOT, capture_output=True, text=True,
                             env={k: v for k, v in os.environ.items() if k != "ADGUARD_ADMIN_HASH"})
    assert refused.returncode != 0 and "ADGUARD_ADMIN_HASH" in refused.stderr
    assert make("dns-plan").returncode != 0 or "DNS_ALLOCATION_REVIEWED" in make("dns-plan").stdout + make("dns-plan").stderr
    assert "adguard_service_address=192.168.0.20" in make("dns-configure", "DNS_CONFIGURE_APPROVED=yes", "DNS_SERVICE_ADDRESS=192.168.0.20",
                                                           env={"ADGUARD_ADMIN_HASH": HASH}).stdout
    print("PASS: AdGuard release pinned, configuration from Git with the login hash from the environment, "
          "LAN-only firewall, unprivileged service, cutover address optional, Make guards")


if __name__ == "__main__":
    main()
