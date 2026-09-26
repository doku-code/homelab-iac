"""Offline K3s profile, join ordering, private-token and lifecycle safety tests."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("lab", ROOT / "scripts/k3s-lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
PROFILE = yaml.safe_load((ROOT / "ansible/vars/k3s-stage-a.yml").read_text())


def fixture():
    # Documentation addresses only; no Terraform output/state or live connection.
    return {"all": {"children": {"k3s_lab": {"hosts": {
        f"server-{i}": {"ansible_host": f"192.0.2.{i}", "ansible_user": "debian",
                         "stage_a_hostname": f"lab-{i}", "stage_a_vm_id": 900 + i}
        for i in (3, 1, 2)
    }}}}}


def profile():
    return {**PROFILE, "k3s_known_networks": ["192.0.2.0/24"], "k3s_admin_cidrs": ["192.0.2.100/32"]}


def rejected(inv, config):
    try:
        lab.prepare(inv, config)
    except ValueError:
        return
    raise AssertionError("Invalid profile accepted")


def main():
    result = lab.prepare(fixture(), profile())["all"]["children"]["k3s_lab"]
    hosts = result["hosts"]
    configs = [hosts[h]["k3s_config"] for h in sorted(hosts)]
    assert sum(c.get("cluster-init", False) for c in configs) == 1
    assert "server" not in configs[0]
    assert all(c["server"] == "https://192.0.2.1:6443" for c in configs[1:])
    unique = {"node-name", "node-ip", "advertise-address", "bind-address", "server", "cluster-init"}
    shared = [{k: v for k, v in c.items() if k not in unique} for c in configs]
    assert shared[0] == shared[1] == shared[2]
    assert configs[0]["disable"] == ["traefik", "servicelb", "local-storage"]
    assert "coredns" not in configs[0]["disable"]
    assert configs[0]["flannel-backend"] == "vxlan"
    assert configs[0]["secrets-encryption"] is True
    assert result["vars"]["ansible_host_key_checking"] is True
    assert "StrictHostKeyChecking=yes" in result["vars"]["ansible_ssh_common_args"]
    for key in ("ansible_host", "stage_a_hostname", "stage_a_vm_id"):
        inv = fixture()
        h = inv["all"]["children"]["k3s_lab"]["hosts"]
        h["server-2"][key] = h["server-1"][key]
        rejected(inv, profile())
    inv = fixture()
    inv["all"]["children"]["k3s_lab"]["hosts"]["server-2"]["k3s_config"] = {}
    rejected(inv, profile())
    for key, value in [("k3s_init_host", "server-3"), ("k3s_pod_cidr", "192.0.2.0/24"),
                       ("k3s_service_cidr", "10.42.0.0/16"), ("k3s_cluster_dns", "192.0.2.10"),
                       ("k3s_sha256", ""), ("k3s_version", "latest"), ("k3s_admin_cidrs", ["0.0.0.0/0"])]:
        rejected(fixture(), {**profile(), key: value})

    env = Environment(undefined=StrictUndefined)
    env.filters["to_nice_yaml"] = yaml.safe_dump
    templates = ROOT / "ansible/roles/k3s_server/templates"
    for config in configs:
        rendered = env.from_string((templates / "config.yaml.j2").read_text()).render(k3s_config=config)
        assert yaml.safe_load(rendered) == config
        assert "token:" not in rendered and "token-file:" in rendered
    firewall = env.from_string((templates / "firewall.nft.j2").read_text()).render(**result["vars"])
    assert "flush ruleset" not in firewall and "tcp dport { 2379, 2380 } drop" in firewall
    assert "udp dport 8472 drop" in firewall and "tcp dport 6443 drop" in firewall
    unit = (templates / "k3s.service.j2").read_text()
    assert "Requires=k3s-lab-firewall.service" in unit and "Restart=always" in unit
    assert "token" not in unit and "cluster-reset" not in unit
    assert "ExecStartPre=" in unit and "etcd/member" in unit and "ExecStartPost=" in unit

    plays = yaml.safe_load((ROOT / "ansible/playbooks/bootstrap-k3s.yml").read_text())
    assert plays[2]["order"] == "sorted" and plays[2]["serial"] == 1
    assert all(p["any_errors_fatal"] for p in plays)
    assert "k3s_install_approved" in str(plays[0]["tasks"])
    assert "not k3s_data.stat.exists or k3s_member.stat.exists" in str(plays[0])
    assert "ansible_play_hosts_all | sort == groups.k3s_lab | sort" in str(plays[0])
    tasks = yaml.safe_load((ROOT / "ansible/roles/k3s_server/tasks/main.yml").read_text())
    for task in tasks:
        if any(k in str(task) for k in ("k3s_bootstrap_token", "k3s_join_token", "k3s_existing_token")):
            assert task.get("no_log") is True, task["name"]
    assert "state: restarted" not in yaml.safe_dump(tasks)
    assert "cluster-reset" not in yaml.safe_dump(tasks)
    downloads = [t["ansible.builtin.get_url"] for t in tasks if "ansible.builtin.get_url" in t]
    assert downloads[0]["checksum"] == "sha256:{{ k3s_sha256 }}"
    snapshots = yaml.safe_load((ROOT / "ansible/playbooks/snapshot-k3s.yml").read_text())
    assert "k3s_snapshot_approved" in str(snapshots)
    assert "snapshot_token_before.content == snapshot_token_after.content" in str(snapshots)
    assert "snapshots.matched == 1" in str(snapshots)
    assert "snapshot_sha256" in str(snapshots) and "token_sha256" in str(snapshots)
    for task in snapshots[0]["tasks"][1]["block"]:
        if any(k in str(task) for k in ("snapshot_token", "recovery_hashes", "ansible.builtin.fetch")):
            assert task.get("no_log") is True, task["name"]

    with tempfile.TemporaryDirectory(prefix="k3s-offline-") as directory:
        private = Path(directory)
        private.chmod(0o700)
        token = private / "bootstrap-token"
        try:
            lab.read_token(token)
        except OSError:
            pass
        else:
            raise AssertionError("Absent token accepted")
        # Deliberately synthetic content, not generation of a real cluster token.
        token.write_text("0" * 64 + "\n")
        token.chmod(0o600)
        assert lab.read_token(token) == "0" * 64
        token.chmod(0o644)
        try:
            lab.read_token(token)
        except ValueError:
            pass
        else:
            raise AssertionError("Public token accepted")
        environment = {"PATH": os.environ["PATH"], "HOME": directory, "ANSIBLE_LOCAL_TEMP": directory}
        for target in ("k3s-token-init", "k3s-install", "k3s-snapshot"):
            denied = subprocess.run(["make", "INFISICAL_PROJECT_ID=offline", target], cwd=ROOT,
                                    env=environment, capture_output=True, text=True)
            assert denied.returncode != 0
            assert "approval" in (denied.stdout + denied.stderr).lower() or "Review K3s" in denied.stdout
            assert "0" * 64 not in denied.stdout + denied.stderr
        missing = subprocess.run(["make", "INFISICAL_PROJECT_ID=offline", "k3s-install", "K3S_INSTALL_APPROVED=yes"],
                                 cwd=ROOT, env=environment, capture_output=True, text=True)
        assert missing.returncode != 0 and "private token prerequisites" in missing.stderr
        assert "PLAY [" not in missing.stdout
        # Exercise actual Ansible template rendering, using only local synthetic data.
        play = private / "render.yml"
        out = private / "config.yaml"
        play.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False,
            "vars": {"k3s_config": configs[0]}, "tasks": [{"ansible.builtin.template": {
                "src": str(templates / "config.yaml.j2"), "dest": str(out), "mode": "0600"}}]}]))
        subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local", str(play)],
                       cwd=ROOT, env=environment, check=True, capture_output=True, text=True)
        assert yaml.safe_load(out.read_text()) == configs[0]
    print("PASS: K3s synthetic render, shared settings, identities/CIDRs, serial order, secrets and approval guards")


if __name__ == "__main__":
    main()
