"""Offline guards for the narrow Proxmox conversion helper and Ansible owner."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/pve_workstation_host"
spec = importlib.util.spec_from_file_location("conversion", ROLE / "files/headless-vms.py")
conversion = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(conversion)


class HeadlessTests(unittest.TestCase):
    def test_only_console_fields_change(self):
        old = {"hostpci0": "mapping=" + conversion.GPU + ",pcie=1",
               "usb0": "mapping=pve-lab-workstation-logitech,usb3=1",
               "hookscript": conversion.HOOK, "scsi0": "disk",
               "efidisk0": "efi", "tpmstate0": "tpm", "memory": 16384}
        remove, options = conversion.changes(old)
        self.assertEqual(remove, ["hookscript", "hostpci0", "usb0"])
        self.assertEqual(options, {"vga": "std,memory=32", "tablet": "1"})
        self.assertEqual(old["scsi0"], "disk")

    def test_idempotent(self):
        self.assertEqual(conversion.changes({"vga": "std,memory=32", "tablet": 1}), ([], {}))

    def test_unrelated_hardware_fails_closed(self):
        for config in ({"hostpci1": "0000:02:00"}, {"usb0": "host=1234:5678"},
                       {"hookscript": "local:snippets/other.sh"}):
            with self.assertRaises(ValueError):
                conversion.changes(config)

    def test_running_vm_rejected_before_mutation(self):
        def read(path):
            if path.endswith("/config"):
                return {"name": "test", "digest": "synthetic"}
            if path.endswith("/pending"):
                return []
            return {"status": "running"}
        with patch.object(conversion.sys, "argv", ["test", "--apply", '{"501":"test"}']), \
             patch.object(conversion.subprocess, "check_output", return_value="pve-lab\n"), \
             patch.object(conversion, "read", side_effect=read), \
             patch.object(conversion.subprocess, "run") as run:
            with self.assertRaisesRegex(AssertionError, "Stop affected VM"):
                conversion.main()
            run.assert_not_called()

    def test_role_approval_and_no_reboot(self):
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        self.assertIn("workstation_headless_approved", str(tasks[0]))
        self.assertFalse(any("ansible.builtin.reboot" in t for t in tasks))
        self.assertFalse(list((ROLE / "templates").glob("*.j2")))
        make = (ROOT / "Makefile").read_text()
        self.assertIn('WORKSTATIONS_HEADLESS_APPROVED', make)

    def test_check_mode_never_writes(self):
        def read(path):
            if path.endswith("/config"):
                return {"name": "test", "digest": "synthetic"}
            if path.endswith("/status/current"):
                return {"status": "stopped"}
            return []
        with patch.object(conversion.sys, "argv", ["test", "--check", '{"501":"test"}']), \
             patch.object(conversion.subprocess, "check_output", return_value="pve-lab\n"), \
             patch.object(conversion, "read", side_effect=read), \
             patch.object(conversion.Path, "glob", return_value=[]), \
             patch.object(conversion.subprocess, "run") as run:
            conversion.main()
            run.assert_not_called()

    def test_wrong_identity_fails_before_writes(self):
        with patch.object(conversion.sys, "argv", ["test", "--apply", '{"501":"expected"}']), \
             patch.object(conversion.subprocess, "check_output", return_value="pve-lab\n"), \
             patch.object(conversion, "read", return_value={"name": "unexpected"}), \
             patch.object(conversion.subprocess, "run") as run:
            with self.assertRaisesRegex(AssertionError, "identity"):
                conversion.main()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
