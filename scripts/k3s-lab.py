"""Stage A inventory and private bootstrap token interfaces. Never print secrets."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def private_directory(path):
    require(path.is_absolute(), "Private directory must be absolute")
    require(not path.is_symlink(), "Private directory cannot be a symlink")
    require(not path.resolve().is_relative_to(ROOT), "Keep private material outside the repository")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
            "Private directory must be owned by this operator with mode 0700")
    return path


def read_token(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600, "Token must be operator-owned mode 0600")
        token = stream.read(1024).strip()
    require(re.fullmatch(r"[0-9a-f]{64}", token), "Missing or invalid lab bootstrap token")
    return token


def prepare(inventory, profile):
    hosts = inventory["all"]["children"]["k3s_lab"]["hosts"]
    require(len(hosts) == 3, "Exactly three servers required")
    ordered = sorted(hosts)
    require(profile["k3s_init_host"] == ordered[0], "Initial server must be first in sorted join order")
    require(re.fullmatch(r"v1\.\d+\.\d+\+k3s\d+", profile["k3s_version"]), "Pin a stable K3s release")
    require(re.fullmatch(r"[0-9a-f]{64}", profile["k3s_sha256"]), "Pin binary SHA256")
    ips = [str(ipaddress.IPv4Address(hosts[h]["ansible_host"])) for h in ordered]
    names = [hosts[h]["stage_a_hostname"] for h in ordered]
    ids = [hosts[h]["stage_a_vm_id"] for h in ordered]
    require(all(len(set(items)) == 3 for items in (ips, names, ids)), "Duplicate server identity")
    require(all(re.fullmatch(r"[a-z][a-z0-9-]{0,61}[a-z0-9]", n) for n in names), "Invalid hostname")
    require(all(hosts[h]["ansible_user"] == "debian" for h in hosts), "Require approved Debian user")
    # Per-host overrides would split shared critical configuration and bypass the profile.
    require(all(not any(k.startswith("k3s_") for k in v) for v in hosts.values()),
            "Per-host K3s overrides are forbidden")
    pod = ipaddress.IPv4Network(profile["k3s_pod_cidr"])
    service = ipaddress.IPv4Network(profile["k3s_service_cidr"])
    known = [ipaddress.IPv4Network(n) for n in profile["k3s_known_networks"]]
    admin = [ipaddress.IPv4Network(n) for n in profile["k3s_admin_cidrs"]]
    require(known and admin and all(n.prefixlen == 32 for n in admin), "Review LANs and individual admin IPs")
    require(not pod.overlaps(service) and all(not n.overlaps(k) for n in (pod, service) for k in known + admin),
            "Pod/service CIDRs overlap each other or known networks")
    require(all(any(ipaddress.ip_address(ip) in n for n in known) for ip in ips), "Node IP outside known networks")
    require(ipaddress.ip_address(profile["k3s_cluster_dns"]) in service, "DNS must be in service CIDR")
    require(profile["k3s_disable"] == ["traefik", "servicelb", "local-storage"], "Review bundled component ownership")
    common = {
        "cluster-cidr": str(pod), "service-cidr": str(service),
        "cluster-dns": profile["k3s_cluster_dns"], "cluster-domain": "cluster.local",
        "flannel-backend": "vxlan", "flannel-external-ip": False,
        "disable-network-policy": False, "disable-cloud-controller": False,
        "disable-helm-controller": False, "egress-selector-mode": "agent",
        "embedded-registry": False, "secrets-encryption": True,
        "secrets-encryption-provider": "aescbc", "disable": profile["k3s_disable"],
        "tls-san": ips + names, "tls-san-security": True,
        "token-file": "/etc/rancher/k3s/lab-token", "write-kubeconfig-mode": "0600",
        "data-dir": "/var/lib/rancher/k3s", "resolv-conf": "/run/systemd/resolve/resolv.conf",
        "etcd-snapshot-schedule-cron": "0 */12 * * *", "etcd-snapshot-retention": 5,
    }
    for host, ip, name in zip(ordered, ips, names):
        config = {**common, "node-name": name, "node-ip": ip, "advertise-address": ip,
                  "bind-address": ip, "flannel-iface": "eth0"}
        if host == profile["k3s_init_host"]:
            config["cluster-init"] = True
        else:
            config["server"] = f"https://{ips[0]}:6443"
        hosts[host].update(k3s_config=config)
    inventory["all"]["children"]["k3s_lab"]["vars"] = {
        **profile, "k3s_peer_ips": ips, "k3s_node_names": names,
        "ansible_host_key_checking": True,
        "ansible_ssh_common_args": "-o StrictHostKeyChecking=yes",
    }
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["token-init", "inventory", "token-check"])
    parser.add_argument("--profile", default=str(ROOT / "ansible/vars/k3s-stage-a.yml"))
    args = parser.parse_args()
    try:
        if args.action == "inventory":
            result = prepare(json.load(sys.stdin), yaml.safe_load(Path(args.profile).read_text()))
            print(json.dumps(result))
            return
        require(os.environ.get("K3S_TOKEN_APPROVED") == "yes", "Explicit lab token approval required")
        directory = private_directory(Path(os.environ.get("K3S_PRIVATE_DIR", "")))
        path = directory / "bootstrap-token"
        if args.action == "token-init":
            # Exclusive creation: never rotate an existing cluster's credential.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_hex(32) + "\n")
        read_token(path)
        print("PASS: private bootstrap token available; value withheld")
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        print("FAIL: invalid inventory/profile or private token prerequisites; see docs/k3s-bootstrap.md", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
