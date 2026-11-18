#!/usr/bin/env python3
"""Offline tests for shared storage (M006): NFS role templates, StorageClass, k3s client package, Make guards."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/nfs_server"


def render(template):
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "out"
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "gather_facts": False, "vars_files": [str(ROLE / "defaults/main.yml")],
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates" / template), "dest": str(out)}}]}]))
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local", str(play)],
                                capture_output=True, text=True, env={**os.environ, "ANSIBLE_NOCOLOR": "1"})
        assert result.returncode == 0, result.stdout + result.stderr
        return out.read_text()


def test_role():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert defaults["nfs_clients"] == ["192.168.0.40/29", "192.168.0.48/31"], "k3s node range .40-.49 only"
    assert "scsi1" in defaults["nfs_data_device"], "the data disk, never the OS disk"
    exports = [line for line in render("exports.j2").splitlines() if line and not line.startswith("#")]
    assert len(exports) == 1 and exports[0].startswith("/srv/k3s 192.168.0.40/29(rw,sync,no_subtree_check,no_root_squash)")
    assert "*" not in exports[0] and "192.168.0.0/24" not in exports[0]
    firewall = render("firewall.nft.j2")
    assert "ip saddr { 192.168.0.40/29, 192.168.0.48/31 } tcp dport 2049 accept" in firewall
    assert "tcp dport { 111, 2049 } drop" in firewall and "flush ruleset" not in firewall
    tasks = {t["name"]: t for t in yaml.safe_load((ROLE / "tasks/main.yml").read_text())}
    filesystem = tasks["Create or grow the data filesystem"]["community.general.filesystem"]
    assert filesystem["force"] is False and filesystem["resizefs"] is True, "never re-format existing data"
    assert "Refuse to continue without the data disk" in tasks


def test_storage_class_and_clients():
    sc = yaml.safe_load((ROOT / "services/storage/storageclass.yaml").read_text())
    assert sc["metadata"]["name"] == "nvme-shared" and sc["provisioner"] == "nfs.csi.k8s.io"
    assert sc["reclaimPolicy"] == "Retain" and sc["parameters"]["onDelete"] == "retain", "user data is never deleted with a PVC"
    assert "storageclass.kubernetes.io/is-default-class" not in sc["metadata"].get("annotations", {})
    example = (ROOT / "terraform/stacks/storage/terraform.tfvars.example").read_text()
    assert f'ipv4         = "{sc["parameters"]["server"]}/24"' in example, "the class points at storage-01"
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert sc["parameters"]["share"] == defaults["nfs_data_mount"]
    assert "nfs-common" in (ROOT / "ansible/roles/k3s/tasks/main.yml").read_text(), "k3s nodes need the NFS client"
    makefile = (ROOT / "Makefile").read_text()
    assert re.search(r"^STORAGE_CSI_CHART_VERSION := \d+\.\d+\.\d+$", makefile, re.M), "the CSI chart is pinned"
    main_tf = (ROOT / "terraform/stacks/storage/main.tf").read_text()
    assert "prevent_destroy = true" in main_tf, "the storage VM holds data"


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="storage-make-") as directory:
        base = Path(directory)
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
        for tool in ("tofu", "helm", "kubectl"):
            (fake / tool).write_text(f'#!/bin/sh\necho "{tool} $*" >> "{base}/calls.log"\n')
            (fake / tool).chmod(0o755)
        (base / "terraform/stacks/storage").mkdir(parents=True)

        def make(*args, env=None):
            return subprocess.run(["make", "--no-print-directory", *args], cwd=base, capture_output=True, text=True,
                                  env={"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base), **(env or {})})

        def calls():
            log = base / "calls.log"
            return log.read_text() if log.exists() else ""

        workstation = {"PROXMOX_VE_API_TOKEN": "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"}
        reviewed = ("storage-plan", "STORAGE_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env")
        assert make("storage-plan").returncode != 0
        (base / "terraform/stacks/storage/terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        result = make(*reviewed, env=workstation)
        assert result.returncode != 0 and "STORAGE_NEW_STATE=yes" in result.stderr and calls() == ""
        make(*reviewed, "STORAGE_NEW_STATE=yes", env=workstation)
        assert "-chdir=terraform/stacks/storage plan -input=false -out=storage.tfplan" in calls()
        assert "-replace" not in calls() and "destroy" not in calls()
        assert "STORAGE_APPLY_APPROVED" in make("storage-apply").stderr
        assert "STORAGE_PLAN_SHA256" in make("storage-apply", "STORAGE_APPLY_APPROVED=yes").stderr
        assert "STORAGE_CONFIGURE_APPROVED" in make("storage-configure").stderr
        assert "STORAGE_CSI_DEPLOY_APPROVED" in make("storage-csi-deploy").stderr and "helm" not in calls()
        make("storage-csi-deploy", "STORAGE_CSI_DEPLOY_APPROVED=yes")
        assert "kubectl --context doku-lab apply -f services/argocd/apps/storage.yaml" in calls(), "Argo CD installs the driver"
        assert "helm" not in calls()


def main():
    test_role()
    test_storage_class_and_clients()
    test_make_guards()
    print("PASS: NFS exports and firewall for k3s nodes only, no re-format, Retain class, pinned CSI chart, Make guards")


if __name__ == "__main__":
    main()
