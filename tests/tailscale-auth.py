"""Exercise the stack-specific auth boundary with synthetic values and no network."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tailscale_auth", ROOT / "scripts/tailscale-proxmox.py")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)
PASSWORD = "synthetic-test-$literal-password"


class Executed(Exception):
    pass


class AuthTests(unittest.TestCase):
    def invoke(self, action, env, plan=None, login_error=False):
        self.executed = None

        def execute(binary, argv, environment):
            self.executed = (argv, environment)
            raise Executed()

        def login(**kwargs):
            if login_error:
                raise RuntimeError(PASSWORD)
            return SimpleNamespace(accessToken="synthetic-session")

        client = SimpleNamespace(auth=SimpleNamespace(universal_auth=SimpleNamespace(login=login)))
        sdk = SimpleNamespace(InfisicalSDKClient=lambda **kwargs: client)
        result = SimpleNamespace(returncode=0, stdout=json.dumps({"configuration": {"root_module": {
            "resources": [{"address": "proxmox_virtual_environment_container.router",
                           "provider_config_key": plan or "proxmox.root"}]}}}))
        with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["wrapper", action]), \
                patch.dict(sys.modules, {"infisical_sdk": sdk}), patch.object(os, "execvpe", execute), \
                patch.object(os, "umask"), patch.object(os, "chdir"), \
                patch.object(auth.subprocess, "run", return_value=result):
            auth.main()

    def test_missing_universal_auth(self):
        with self.assertRaisesRegex(ValueError, "INFISICAL_CLIENT_ID"):
            self.invoke("plan", {"PROXMOX_ROOT_PASSWORD": PASSWORD})
        self.assertIsNone(self.executed)

    def test_infisical_injects_selected_path_without_ambient_fallback(self):
        with self.assertRaises(Executed):
            self.invoke("plan", {"INFISICAL_CLIENT_ID": "synthetic-id", "INFISICAL_CLIENT_SECRET": PASSWORD,
                                 "PROXMOX_ROOT_PASSWORD": PASSWORD, "PROXMOX_VE_API_TOKEN": "synthetic-token"})
        argv, env = self.executed
        self.assertEqual(argv[argv.index("--path") + 1], "/proxmox/")
        self.assertEqual(argv[argv.index("--env") + 1], "dev")
        self.assertIn("--expand=false", argv)
        self.assertIn("--include-imports=false", argv)
        self.assertNotIn(PASSWORD, repr(argv))
        self.assertNotIn("PROXMOX_ROOT_PASSWORD", env)
        self.assertNotIn("PROXMOX_VE_API_TOKEN", env)
        self.assertNotIn("INFISICAL_CLIENT_SECRET", env)
        self.assertEqual(env["INFISICAL_TOKEN"], "synthetic-session")

    def test_password_only_process_environment(self):
        with self.assertRaises(Executed):
            self.invoke("provider-plan", {"PROXMOX_ROOT_PASSWORD": PASSWORD,
                        "PROXMOX_VE_API_TOKEN": "synthetic-token", "PM_VE_API_TOKEN": "legacy-token",
                        "PROXMOX_VE_AUTH_TICKET": "ticket", "INFISICAL_TOKEN": "session"})
        argv, env = self.executed
        self.assertEqual(env, {"PROXMOX_VE_PASSWORD": PASSWORD, "PROXMOX_VE_USERNAME": "root@pam"})
        self.assertNotIn(PASSWORD, repr(argv))
        self.assertEqual(argv[-2:], ["-input=false", "-out=tailscale.tfplan"])

    def test_missing_injected_password(self):
        for value in ("", " "):
            with self.assertRaisesRegex(ValueError, "PROXMOX_ROOT_PASSWORD"):
                self.invoke("provider-plan", {"PROXMOX_ROOT_PASSWORD": value, "PROXMOX_VE_PASSWORD": PASSWORD})

    def test_logs_and_cli_injection_denied(self):
        for key in ("TF_LOG", "TF_LOG_PROVIDER", "TF_CLI_ARGS_plan"):
            with self.assertRaisesRegex(ValueError, "Unset TF_LOG"):
                self.invoke("provider-plan", {"PROXMOX_ROOT_PASSWORD": PASSWORD, key: "TRACE"})

    def test_apply_guards_and_old_plan(self):
        with self.assertRaisesRegex(ValueError, "approval"):
            self.invoke("apply", {})
        with self.assertRaisesRegex(ValueError, "approval"):
            self.invoke("provider-apply", {"PROXMOX_ROOT_PASSWORD": PASSWORD})
        with self.assertRaisesRegex(ValueError, "NEW plan"):
            self.invoke("provider-apply", {"PROXMOX_ROOT_PASSWORD": PASSWORD,
                                           "TAILSCALE_APPLY_APPROVED": "yes"}, plan="proxmox")
        with self.assertRaises(Executed):
            self.invoke("provider-apply", {"PROXMOX_ROOT_PASSWORD": PASSWORD,
                                           "TAILSCALE_APPLY_APPROVED": "yes"})
        self.assertEqual(self.executed[0][-1], "tailscale.tfplan")

    def test_sdk_error_does_not_disclose_credentials(self):
        with self.assertRaisesRegex(ValueError, "Universal Auth failed") as error:
            self.invoke("plan", {"INFISICAL_CLIENT_ID": "synthetic-id",
                                 "INFISICAL_CLIENT_SECRET": PASSWORD}, login_error=True)
        self.assertNotIn(PASSWORD, str(error.exception))


if __name__ == "__main__":
    unittest.main()
