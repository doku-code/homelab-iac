"""Mocked Terraform plans in disposable code-only roots, never real states."""
from pathlib import Path
import os
import hashlib
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "terraform/stacks/pve-lab-workstations/vms.tf").read_text()
    # Snapshot the pre-change ordinary VM model, excluding only hardware blocks.
    ordinary = source[:source.index('  dynamic "hostpci"')] + source[source.index('  efi_disk {'):]
    assert hashlib.sha256(ordinary.encode()).hexdigest() == "486a0b319789a20fb0ef058b3d4654f7767c1d7cbaf7bca9c7dda6294ee6fa25"
    assert hashlib.sha256((ROOT / "terraform/stacks/pve-lab-workstations/locals.tf").read_bytes()).hexdigest() == "1b906b3f6a14a60d12b7ebc15a8068f0644eebd8448346222e9f267ef58545c8"
    for clause in ["prevent_destroy = true", "started,", "cpu[0].affinity,", "hook_script_file_id,", "for_each = local.workstation_vms"]:
        assert clause in source, clause
    headless = (ROOT / "terraform/stacks/pve-lab-controller/main.tf").read_text()
    assert "hostpci" not in headless and "hook_script_file_id" not in headless
    with tempfile.TemporaryDirectory(prefix="vm-profiles-") as directory:
        base = Path(directory)
        (base / "keys").mkdir()
        shutil.copyfile(ROOT / "keys/doku-lab-admin.pub", base / "keys/doku-lab-admin.pub")
        env = {"PATH": os.environ["PATH"], "HOME": str(base), "TF_IN_AUTOMATION": "1"}
        for name in ["pve-lab-workstations", "pve-lab-controller"]:
            src = ROOT / "terraform/stacks" / name
            dst = base / "terraform/stacks" / name
            dst.mkdir(parents=True)
            for file in [*src.glob("*.tf"), src / ".terraform.lock.hcl"]:
                shutil.copyfile(file, dst / file.name)
            shutil.copytree(src / "tests", dst / "tests")
            for command in [["init", "-backend=false", "-input=false", "-lockfile=readonly"], ["test", "-no-color"]]:
                subprocess.run(["terraform", f"-chdir={dst}", *command], env=env, check=True)
    print("PASS: isolated mocked VM profiles and lifecycle guards")


if __name__ == "__main__":
    main()
