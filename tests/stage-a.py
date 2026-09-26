"""Offline Stage A baseline, inventory shape and fail-closed command guards."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile

import yaml
from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[1]


def main():
    role = yaml.safe_load((ROOT / "ansible/roles/headless_baseline/tasks/main.yml").read_text())
    assert role[0]["ansible.builtin.apt"] == {"update_cache": True, "cache_valid_time": 0}
    assert set(role[1]["ansible.builtin.apt"]["name"]) == {
        "ca-certificates", "curl", "python3", "qemu-guest-agent", "systemd-timesyncd"
    }
    hostname = role[2]["ansible.builtin.hostname"]["name"]
    assert Template(hostname, undefined=StrictUndefined).render(stage_a_hostname="lab-server-1") == "lab-server-1"
    play = yaml.safe_load((ROOT / "ansible/playbooks/configure-k3s-lab.yml").read_text())[0]
    assert play["hosts"] == "k3s_lab" and play["roles"] == ["headless_baseline"]
    assert play["serial"] == 1 and play["become"] is True
    assert "stage_a_configure_approved" in str(play["pre_tasks"])
    start = yaml.safe_load((ROOT / "ansible/playbooks/start-k3s-lab.yml").read_text())[0]
    assert start["hosts"] == "k3s_lab" and start["serial"] == 1
    commands = [t["ansible.builtin.command"]["argv"] for t in start["tasks"] if "ansible.builtin.command" in t]
    assert [c[:2] for c in commands] == [["qm", "config"], ["qm", "status"], ["qm", "start"]]
    assert all(c[2] == "{{ stage_a_vm_id | string }}" for c in commands)
    assert "stage_a_start_approved" in str(start["tasks"][0])
    assert "stage_a_hostname" in str(start["tasks"][2])
    module = (ROOT / "terraform/modules/headless-vm/main.tf").read_text()
    for forbidden in ("hostpci", "usb", "hook_script", "workstation", "local-exec", "remote-exec"):
        assert forbidden not in module, forbidden
    assert "prevent_destroy = true" in module
    assert "ignore_changes  = [started]" in module
    make = (ROOT / "Makefile").read_text()
    plan = make.split("stage-a-plan:\n", 1)[1].split("\nstage-a-apply:", 1)[0]
    assert plan.index("rm -f") < plan.index(" init ") < plan.index(" plan ")
    assert "|| { rm -f" in plan
    assert "STAGE_A_PLAN_SHA256" in make and "shasum -a 256 -c" in make
    assert 'output -json ansible_inventory > "$$inventory"' in make
    assert make.count('inventory="$$work/inventory.json"') == 2
    with tempfile.TemporaryDirectory(prefix="stage-a-inventory-") as directory:
        inventory = Path(directory) / "inventory.json"
        inventory.write_text(json.dumps({"all": {"children": {"k3s_lab": {"hosts": {
            f"server-{i}": {"ansible_host": f"192.0.2.{10+i}", "ansible_user": "debian",
                             "stage_a_hostname": f"lab-server-{i}", "stage_a_vm_id": 900+i,
                             "proxmox_node": "mock-node"}
            for i in range(1, 4)
        }}}}}))
        env = {"PATH": os.environ["PATH"], "HOME": directory, "ANSIBLE_LOCAL_TEMP": directory}
        parsed = json.loads(subprocess.check_output(
            [str(ROOT / ".venv/bin/ansible-inventory"), "-i", str(inventory), "--list"],
            cwd=ROOT, env=env, text=True
        ))
        assert parsed["k3s_lab"]["hosts"] == ["server-1", "server-2", "server-3"]
        assert parsed["_meta"]["hostvars"]["server-2"]["stage_a_vm_id"] == 902
        assert parsed["_meta"]["hostvars"]["server-2"]["ansible_host"] == "192.0.2.12"
    with tempfile.TemporaryDirectory(prefix="stage-a-guards-") as home:
        # Drop all runtime credentials and Make overrides; denial happens before any command.
        env = {"PATH": os.environ["PATH"], "HOME": home}
        for target in ("plan", "apply", "start", "configure"):
            command = ["make", "INFISICAL_PROJECT_ID=offline", f"stage-a-{target}"]
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            assert result.returncode != 0, target
            assert "Error 1" in result.stderr, result.stderr
            dry = subprocess.check_output(["make", "-n", *command[1:]], cwd=ROOT, env=env, text=True)
            assert "terraform destroy" not in dry and "workstations-" not in dry
            assert "StrictHostKeyChecking=no" not in dry and "ANSIBLE_HOST_KEY_CHECKING=False" not in dry
    with tempfile.TemporaryDirectory(prefix="stage-a-failed-plan-") as directory:
        # Exercise recipe error handling with stub executables in a disposable repository.
        base = Path(directory)
        shutil.copyfile(ROOT / "Makefile", base / "Makefile")
        stack = base / "terraform/stacks/pve-lab-k3s"
        stack.mkdir(parents=True)
        (stack / "terraform.tfvars").write_text("# synthetic only\n")
        saved = stack / "stage-a.tfplan"
        bin_dir = base / "bin"
        bin_dir.mkdir()
        terraform = bin_dir / "terraform"
        terraform.write_text('''#!/bin/bash
set -eu
dir="${1#-chdir=}"
shift
case "$1" in
  init) test ! -e "$dir/stage-a.tfplan"; exit "${INIT_FAILURE:-0}" ;;
  plan) printf 'partial synthetic plan' > "$dir/stage-a.tfplan"; exit 1 ;;
  *) exit 99 ;;
esac
''')
        infisical = bin_dir / "infisical"
        infisical.write_text('''#!/bin/bash
set -eu
if [ "$1" = login ]; then printf 'synthetic-token'; exit 0; fi
while [ "$1" != -- ]; do shift; done
shift
exec "$@"
''')
        terraform.chmod(0o700)
        infisical.chmod(0o700)
        env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": directory,
               "INFISICAL_CLIENT_ID": "synthetic", "INFISICAL_CLIENT_SECRET": "synthetic"}
        for failure in ("1", "0"):
            saved.write_text("stale synthetic plan")
            result = subprocess.run(
                ["make", "INFISICAL_PROJECT_ID=offline", "stage-a-plan", "STAGE_A_ALLOCATION_REVIEWED=yes"],
                cwd=base, env={**env, "INIT_FAILURE": failure}, capture_output=True, text=True
            )
            assert result.returncode != 0 and not saved.exists(), result.stderr
    print("PASS: baseline render/packages, generated inventory interface, scoped start, denied live gates and Make dry-runs")


if __name__ == "__main__":
    main()
