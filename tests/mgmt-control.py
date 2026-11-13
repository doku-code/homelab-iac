"""Offline tests for the pve-management bootstrap: auth guard, discovery logic and Make guards.

No credentials, no network: Make targets run in a temporary copy with fake terraform/tofu
binaries that only record how they were called.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True  # loading scripts/ must not leave __pycache__ in the repository
TOKEN = "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_guard():
    guard = load("pve_auth_guard", "scripts/pve-auth-guard.py")
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN}) == []
    assert guard.check({}), "missing token must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": "root@pam!x=1"}), "root@pam token must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": "not-a-token"})
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "PROXMOX_VE_PASSWORD": "x"}), "password auth must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "PROXMOX_VE_INSECURE": "true"}), "insecure TLS must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "TF_LOG": "DEBUG"}), "debug logging must be refused"
    env = guard.child_env({"PROXMOX_VE_API_TOKEN": TOKEN, "INFISICAL_CLIENT_SECRET": "x", "PATH": "/bin"})
    assert "INFISICAL_CLIENT_SECRET" not in env and env["PROXMOX_VE_API_TOKEN"] == TOKEN
    # Problems never echo the secret part of a token.
    for problem in guard.check({"PROXMOX_VE_API_TOKEN": "root@pam!x=SUPERSECRETVALUE"}):
        assert "SUPERSECRETVALUE" not in problem


def test_discovery_logic():
    discover = load("pve_discover", "scripts/pve-discover.py")
    required = discover.required_privileges("pve-management", "local", "local-lvm", "vmbr0")
    assert set(required) == {"/vms", "/nodes/pve-management", "/storage/local", "/storage/local-lvm",
                             "/sdn/zones/localnetwork/vmbr0"}
    assert "Sys.AccessNetwork" in required["/nodes/pve-management"]
    assert "Sys.Modify" not in sum(required.values(), []), "download-url must not require Sys.Modify on /"
    full = {path: {priv: 1 for priv in privs} for path, privs in required.items()}
    assert discover.missing_privileges(required, full) == {}
    partial = dict(full, **{"/vms": {"VM.Audit": 1}})
    assert "VM.Allocate" in discover.missing_privileges(required, partial)["/vms"]
    report = discover.summarize(
        {"version": "9.1.1"}, [{"type": "node", "name": "pve-management"}],
        [{"storage": "local", "type": "dir", "content": "iso,import,vztmpl", "active": 1, "avail": 1},
         {"storage": "local-lvm", "type": "lvmthin", "content": "images,rootdir", "active": 1, "avail": 1}],
        [{"iface": "vmbr0"}], [{"vmid": 101}], "100")
    assert report["standalone"] and report["storages_with_import"] == ["local"] and report["bridges"] == ["vmbr0"]
    assert not discover.summarize({}, [{"type": "cluster"}], [], [], [], "100")["standalone"]


def make_sandbox(base):
    shutil.copyfile(ROOT / "Makefile", base / "Makefile")
    (base / "services/windmill").mkdir(parents=True)
    shutil.copyfile(ROOT / "services/windmill/targets.mk", base / "services/windmill/targets.mk")
    (base / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/pve-auth-guard.py", base / "scripts/pve-auth-guard.py")
    (base / ".venv/bin").mkdir(parents=True)
    (base / ".venv/bin/python").symlink_to(sys.executable)
    (base / ".infisical.json").write_text('{"workspaceId": "offline"}')
    fake = base / "fake-bin"
    fake.mkdir()
    for tool in ("terraform", "tofu"):
        script = fake / tool
        script.write_text(f'#!/bin/sh\necho "{tool} $*" >> "{base}/calls.log"\n')
        script.chmod(0o755)
    for stack in ("pve-lab-controller", "pve-compute-forgejo-runner", "pve-management-control"):
        (base / "terraform/stacks" / stack).mkdir(parents=True)
    return fake


def run_make(base, fake, *args, extra_env=None):
    env = {"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base)}
    env.update(extra_env or {})
    return subprocess.run(["make", "--no-print-directory", *args], cwd=base, env=env,
                          capture_output=True, text=True)


def calls(base):
    log = base / "calls.log"
    return log.read_text() if log.exists() else ""


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="mgmt-control-") as directory:
        base = Path(directory)
        fake = make_sandbox(base)

        # A legacy root still pointed at 192.168.0.10 (now pve-management) is refused before Terraform runs.
        (base / "terraform/stacks/pve-lab-controller/terraform.tfvars").write_text(
            'proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        result = run_make(base, fake, "controller-plan", "CONTROLLER_ALLOCATION_REVIEWED=yes")
        assert result.returncode != 0 and "retired host address" in result.stderr, result.stderr
        assert calls(base) == ""

        # The JSON tfvars form is covered too (pve-core-windmill uses terraform.tfvars.json).
        (base / "terraform/stacks/pve-core-windmill").mkdir(parents=True)
        (base / "terraform/stacks/pve-core-windmill/terraform.tfvars.json").write_text(
            '{"proxmox_endpoint": "https://192.168.0.10:8006/"}')
        result = run_make(base, fake, "windmill-plan")
        assert result.returncode != 0 and "retired host address" in result.stderr, result.stderr
        assert calls(base) == ""
        # A legacy root on the current cluster API is not blocked by the guard.
        (base / "terraform/stacks/pve-core-windmill/terraform.tfvars.json").write_text(
            '{"proxmox_endpoint": "https://192.168.0.11:8006/"}')
        run_make(base, fake, "windmill-plan")
        assert "terraform -chdir=terraform/stacks/pve-core-windmill init" in calls(base)
        (base / "calls.log").unlink()

        # Roots recorded on retired pve-compute refuse live operations outright.
        result = run_make(base, fake, "runner-live-plan")
        assert result.returncode != 0 and "retired pve-compute" in result.stderr
        assert calls(base) == ""

        mgmt = base / "terraform/stacks/pve-management-control"
        (mgmt / "terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')

        # Plan requires reviewed allocation and an explicit credential source.
        assert run_make(base, fake, "mgmt-plan").returncode != 0
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes")
        assert result.returncode != 0 and "MGMT_INPUT_SOURCE" in result.stderr
        assert calls(base) == ""

        # A root@pam token is refused by the guard: tofu init may run, tofu plan never does.
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env",
                          extra_env={"PROXMOX_VE_API_TOKEN": "root@pam!x=1"})
        assert result.returncode != 0 and "dedicated automation identity" in result.stderr, result.stderr
        assert " plan " not in calls(base)

        # With a dedicated token, the plan is saved to a file for exact-plan approval.
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env",
                          extra_env={"PROXMOX_VE_API_TOKEN": TOKEN})
        assert f"-chdir=terraform/stacks/pve-management-control plan -input=false -out=mgmt.tfplan" in calls(base)
        assert "PROXMOX_VE_API_TOKEN" not in result.stdout + result.stderr and TOKEN not in result.stdout + result.stderr

        # Apply needs explicit approval and the matching plan hash; nothing reaches tofu apply otherwise.
        assert run_make(base, fake, "mgmt-apply", "MGMT_INPUT_SOURCE=env").returncode != 0
        (mgmt / "mgmt.tfplan").write_text("synthetic plan")
        result = run_make(base, fake, "mgmt-apply", "MGMT_APPLY_APPROVED=yes", "MGMT_PLAN_SHA256=" + "0" * 64,
                          "MGMT_INPUT_SOURCE=env", extra_env={"PROXMOX_VE_API_TOKEN": TOKEN})
        assert result.returncode != 0 and " apply " not in calls(base)

        # The state backup refuses without an off-machine destination and recipients.
        assert run_make(base, fake, "mgmt-state-backup").returncode != 0


def main():
    test_auth_guard()
    test_discovery_logic()
    test_make_guards()
    print("PASS: pve-management auth guard, discovery logic and Make guards")


if __name__ == "__main__":
    main()
