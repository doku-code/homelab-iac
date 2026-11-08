"""Offline checks only; validate isolation, persistence and initial-plan guard."""
import copy
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
guard = runpy.run_path(str(ROOT / "scripts/windmill-plan.py"))["guard_plan"]
verify = runpy.run_path(str(ROOT / "services/windmill/verify.py"))["main"]


class WindmillTests(unittest.TestCase):
    def test_private_service(self):
        compose = yaml.safe_load((ROOT / "services/windmill/compose.yml").read_text())
        services = compose["services"]
        self.assertEqual(set(services), {"server", "worker", "db"})
        self.assertEqual(services["server"]["ports"], ["127.0.0.1:8000:8000"])
        self.assertNotIn("ports", services["worker"])
        self.assertNotIn("ports", services["db"])
        self.assertEqual(services["db"]["volumes"], ["db_data:/var/lib/postgresql"])
        self.assertTrue(compose["volumes"]["db_data"]["external"])
        self.assertEqual(services["worker"]["environment"]["WORKER_GROUP"], "default")
        for service in services.values():
            self.assertIn("@sha256:", service["image"])
            self.assertFalse(service.get("privileged"))
            self.assertNotIn("docker.sock", str(service))

    def test_new_resource_only(self):
        allocation = {"ctid": 9999}
        change = {"address": "proxmox_virtual_environment_container.windmill",
                  "change": {"actions": ["create"], "after": {"vm_id": 9999, "node_name": "pve-core",
                             "initialization": [{"hostname": "windmill", "ip_config": [
                                 {"ipv4": [{"address": "dhcp"}]}]}]}}}
        plan = {"resource_changes": [change]}
        guard(plan, allocation)
        for actions in (["update"], ["delete", "create"], ["delete"]):
            bad = copy.deepcopy(plan)
            bad["resource_changes"][0]["change"]["actions"] = actions
            with self.assertRaises(SystemExit):
                guard(bad, allocation)
        for bad in ({"resource_changes": [change, change]}, {**plan, "resource_drift": [change]}):
            with self.assertRaises(SystemExit):
                guard(bad, allocation)
        with self.assertRaises(SystemExit):
            guard(plan, {**allocation, "ctid": 9998})

    def test_worker_proof(self):
        job = "00000001-1111-4111-8111-111111111111"
        for group, passed in (("default", True), ("other", False)):
            def fake_request(path, body=None, token=None):
                if path == "/":
                    return "<html>"
                if path == "/api/version":
                    return "1.864.1"
                if path == "/api/auth/login":
                    return "synthetic-session"
                if path.endswith("/run/preview"):
                    self.assertEqual(body["language"], "bash")
                    return job
                if path.endswith("/completed/get/" + job):
                    return json.dumps({"success": True, "result": "windmill-smoke-ok", "worker": "test"})
                if path == "/api/workers/list":
                    return json.dumps([{"worker": "test", "worker_group": group}])
                raise AssertionError("Unexpected API path")
            with patch.dict(verify.__globals__, request=fake_request), patch("builtins.print"), \
                 patch("sys.stdin", io.StringIO(json.dumps("synthetic-password-for-unit-test"))):
                if passed:
                    verify()
                else:
                    with self.assertRaisesRegex(RuntimeError, "default worker"):
                        verify()


if __name__ == "__main__":
    unittest.main()
