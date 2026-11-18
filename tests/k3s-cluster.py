#!/usr/bin/env python3
"""Offline tests for the doku-lab k3s cluster (M004): role, playbook, templates, host-key pinning, Make guards.

No infrastructure calls: templates render on localhost, Make runs in a sandbox with a fake tofu.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/k3s"
TOKEN = "a" * 64


def render(template, extra_vars):
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "out"
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "gather_facts": False, "vars_files": [str(ROLE / "defaults/main.yml")],
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates" / template), "dest": str(out)}}]}]))
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local",
                                 "-e", json.dumps(extra_vars), str(play)],
                                capture_output=True, text=True,
                                env={**os.environ, "ANSIBLE_NOCOLOR": "1", "K3S_TOKEN": TOKEN})
        assert result.returncode == 0, result.stdout + result.stderr
        return out.read_text()


def test_config_template():
    base = {"ansible_host": "192.168.0.40", "k3s_init_node": "localhost", "k3s_role": "server"}
    init = yaml.safe_load(render("config.yaml.j2", base))
    assert init["cluster-init"] is True and "server" not in init, "the first server initialises embedded etcd"
    assert init["token"] == TOKEN and init["node-ip"] == "192.168.0.40" and init["tls-san"] == ["192.168.0.40"]
    assert init["write-kubeconfig-mode"] == "0600" and "disable" not in init, "Traefik and ServiceLB stay (M004)"
    assert init["cluster-cidr"] == "10.42.0.0/16" and init["service-cidr"] == "10.43.0.0/16"

    # A later server joins the first one through its API (hostvars of the init node).
    join = yaml.safe_load(render("config.yaml.j2", {**base, "k3s_init_node": "other",
                                                    "k3s_api_url": "https://192.168.0.40:6443",
                                                    "ansible_host": "192.168.0.41"}))
    assert "cluster-init" not in join and join["server"] == "https://192.168.0.40:6443"
    agent = yaml.safe_load(render("config.yaml.j2", {**base, "k3s_role": "agent", "k3s_init_node": "other",
                                                     "k3s_api_url": "https://192.168.0.40:6443"}))
    assert agent["server"] == "https://192.168.0.40:6443" and "tls-san" not in agent

    traefik = yaml.safe_load(yaml.safe_load(render("traefik-config.yaml.j2", base))["spec"]["valuesContent"])
    assert traefik["service"]["spec"]["externalTrafficPolicy"] == "Local", "ingress allow-lists need the client address"
    assert traefik["deployment"]["kind"] == "DaemonSet", "with the Local policy every node needs its own Traefik"

    unit = render("k3s.service.j2", base)
    assert "ExecStart=/usr/local/bin/k3s server --config /etc/rancher/k3s/config.yaml" in unit and "Type=notify" in unit


def test_role():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    legacy = yaml.safe_load((ROOT / "ansible/vars/k3s-stage-a.yml").read_text())
    assert defaults["k3s_version"] == legacy["k3s_version"] and defaults["k3s_sha256"] == legacy["k3s_sha256"]
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    by_name = {t["name"]: t for t in tasks}
    for name in ("Require the cluster token from the environment", "Write the k3s configuration (cluster token)"):
        assert by_name[name].get("no_log") is True, name
    config = by_name["Write the k3s configuration (cluster token)"]["ansible.builtin.template"]
    assert config["mode"] == "0600" and config["dest"] == "/etc/rancher/k3s/config.yaml"
    binary = by_name["Install the pinned k3s binary, verified by SHA256 (no upstream install script)"]["ansible.builtin.get_url"]
    assert binary["checksum"] == "sha256:{{ k3s_sha256 }}"
    assert "get.k3s.io" not in (ROLE / "tasks/main.yml").read_text()


def test_playbook():
    plays = yaml.safe_load((ROOT / "ansible/playbooks/configure-k3s.yml").read_text())
    nodes, kubeconfig = plays
    assert nodes["hosts"] == "k3s_cluster" and nodes["serial"] == 1 and nodes["order"] == "sorted"
    assert nodes["roles"] == ["headless_baseline", "k3s"] and nodes["any_errors_fatal"] is True
    tasks = kubeconfig["tasks"]
    assert tasks[0]["ansible.builtin.meta"] == "end_host" and "k3s_init_node" in tasks[0]["when"]
    write = tasks[-1]
    assert write["ansible.builtin.copy"]["mode"] == "0600" and write["no_log"] is True
    assert write["delegate_to"] == "localhost" and write["become"] is False
    assert "https://127.0.0.1:6443" in write["ansible.builtin.copy"]["content"], "the API is rewritten to the node IP"

    # Run the playbook's exact transform over a k3s-shaped kubeconfig: every reference must be renamed,
    # including the "- name: default" list items (a missed user makes kubectl prompt for a username).
    sample = ("apiVersion: v1\nclusters:\n- cluster:\n    certificate-authority-data: Q0E=\n"
              "    server: https://127.0.0.1:6443\n  name: default\ncontexts:\n- context:\n    cluster: default\n"
              "    user: default\n  name: default\ncurrent-context: default\nkind: Config\npreferences: {}\n"
              "users:\n- name: default\n  user:\n    client-certificate-data: Q0VSVA==\n    client-key-data: S0VZ\n")
    expression = write["ansible.builtin.copy"]["content"]
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "kubeconfig"
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "gather_facts": False, "vars": kubeconfig["vars"],
            "tasks": [{"ansible.builtin.copy": {"dest": str(out), "content": expression}}]}]))
        extra = {"ansible_host": "192.168.0.40",
                 "k3s_admin_kubeconfig": {"content": __import__("base64").b64encode(sample.encode()).decode()}}
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local",
                                 "-e", json.dumps(extra), str(play)], capture_output=True, text=True,
                                env={**os.environ, "ANSIBLE_NOCOLOR": "1"})
        assert result.returncode == 0, result.stdout + result.stderr
        config = yaml.safe_load(out.read_text())
    assert config["current-context"] == "doku-lab"
    assert config["clusters"][0]["name"] == "doku-lab" and config["clusters"][0]["cluster"]["server"] == "https://192.168.0.40:6443"
    assert config["contexts"][0] == {"name": "doku-lab", "context": {"cluster": "doku-lab", "user": "doku-lab"}}
    assert config["users"][0]["name"] == "doku-lab" and config["users"][0]["user"]["client-key-data"] == "S0VZ"


def test_hostkey_script_refuses_old_environment():
    script = ROOT / "scripts/pin-guest-hostkey.sh"
    for args in (["192.168.0.14", "310", "192.168.0.40"], ["192.168.0.16", "31x", "192.168.0.40"],
                 ["192.168.0.16", "310", "10.0.0.1"]):
        result = subprocess.run([str(script), *args], capture_output=True, text=True)
        assert result.returncode == 2 and "refused" in result.stderr, args


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="k3s-make-") as directory:
        base = Path(directory)
        shutil.copyfile(ROOT / "Makefile", base / "Makefile")
        (base / "services/windmill").mkdir(parents=True)
        shutil.copyfile(ROOT / "services/windmill/targets.mk", base / "services/windmill/targets.mk")
        (base / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/pve-auth-guard.py", base / "scripts/pve-auth-guard.py")
        (base / ".venv/bin").mkdir(parents=True)
        (base / ".venv/bin/python").symlink_to(sys.executable)
        (base / ".venv/bin/ansible-playbook").write_text(f'#!/bin/sh\necho "ansible $*" >> "{base}/calls.log"\n')
        (base / ".venv/bin/ansible-playbook").chmod(0o755)
        (base / ".infisical.json").write_text('{"workspaceId": "offline"}')
        fake = base / "fake-bin"
        fake.mkdir()
        (fake / "tofu").write_text(f'#!/bin/sh\necho "tofu $*" >> "{base}/calls.log"\necho "{{}}"\n')
        (fake / "tofu").chmod(0o755)
        root = base / "terraform/stacks/k3s"
        root.mkdir(parents=True)

        def make(*args, env=None):
            return subprocess.run(["make", "--no-print-directory", *args], cwd=base, capture_output=True, text=True,
                                  env={"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base), **(env or {})})

        def calls():
            log = base / "calls.log"
            return log.read_text() if log.exists() else ""

        workstation = {"PROXMOX_VE_API_TOKEN": "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"}
        reviewed = ("k3s-cluster-plan", "K3S_CLUSTER_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env")
        assert make("k3s-cluster-plan").returncode != 0
        assert "terraform.tfvars" in make(*reviewed, env=workstation).stderr
        (root / "terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        result = make(*reviewed, env=workstation)
        assert result.returncode != 0 and "K3S_CLUSTER_NEW_STATE=yes" in result.stderr and calls() == ""
        result = make(*reviewed, "K3S_CLUSTER_NEW_STATE=yes", env=workstation)
        assert "-chdir=terraform/stacks/k3s plan -input=false -out=k3s.tfplan" in calls(), result.stderr
        assert "-replace" not in calls()
        # Rebuild: exactly one named VM; anything else is refused before tofu runs.
        bad = make(*reviewed, "K3S_CLUSTER_NEW_STATE=yes", "K3S_CLUSTER_REPLACE=mgmt-control-01", env=workstation)
        assert bad.returncode != 0 and "K3S_CLUSTER_REPLACE" in bad.stderr
        make(*reviewed, "K3S_CLUSTER_NEW_STATE=yes", "K3S_CLUSTER_REPLACE=k3s-server-01", env=workstation)
        assert '-replace=proxmox_virtual_environment_vm.node["k3s-server-01"]' in calls()

        assert "K3S_CLUSTER_APPLY_APPROVED" in make("k3s-cluster-apply").stderr
        assert "K3S_CLUSTER_PLAN_SHA256" in make("k3s-cluster-apply", "K3S_CLUSTER_APPLY_APPROVED=yes").stderr
        assert "apply" not in calls().split("plan")[-1]

        assert "K3S_CLUSTER_CONFIGURE_APPROVED" in make("k3s-cluster-configure").stderr
        result = make("k3s-cluster-configure", "K3S_CLUSTER_CONFIGURE_APPROVED=yes")
        assert result.returncode != 0 and "K3S_TOKEN" in result.stderr and "ansible" not in calls()
        result = make("k3s-cluster-configure", "K3S_CLUSTER_CONFIGURE_APPROVED=yes", env={"K3S_TOKEN": TOKEN})
        assert "ansible -i" in calls() and "configure-k3s.yml" in calls(), result.stderr
        assert TOKEN not in result.stdout + result.stderr


def main():
    test_config_template()
    test_role()
    test_playbook()
    test_hostkey_script_refuses_old_environment()
    test_make_guards()
    print("PASS: k3s config/unit templates, pinned binary and no_log, kubeconfig hand-off, host-key refusals, Make guards")


if __name__ == "__main__":
    main()
