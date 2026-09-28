"""Exercise real Make recipes with synthetic credentials and offline executables only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "test@pve!offline=synthetic-not-a-credential"


def main():
    with tempfile.TemporaryDirectory(prefix="stage-a-inputs-") as directory:
        base = Path(directory)
        shutil.copyfile(ROOT / "Makefile", base / "Makefile")
        (base / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/stage-a-inputs.py", base / "scripts/stage-a-inputs.py")
        (base / ".venv/bin").mkdir(parents=True)
        (base / ".venv/bin/python").symlink_to(sys.executable)
        stack = base / "terraform/stacks/pve-lab-k3s"
        stack.mkdir(parents=True)
        profile = stack / "terraform.tfvars"
        profile.write_text('# Synthetic native configuration, never real inputs\n')
        saved = stack / "stage-a.tfplan"
        trace = base / "trace"
        bin_dir = base / "bin"
        bin_dir.mkdir()
        # No real Terraform/Infisical can be found if a stub is missing.
        for executable in ("rm", "shasum", "perl"):
            (bin_dir / executable).symlink_to(shutil.which(executable))
        (base / "infisical_sdk.py").write_text('''import os
from types import SimpleNamespace
class InfisicalSDKClient:
    def __init__(self, host):
        assert host == "https://secrets.invalid"
        self.auth = SimpleNamespace(universal_auth=self)
    def login(self, client_id, client_secret):
        assert client_id == "synthetic-id" and client_secret == "synthetic-client-secret"
        if os.environ.get("LOGIN_FAILURE"):
            raise RuntimeError("synthetic-client-secret must never be printed")
        return SimpleNamespace(accessToken="synthetic-session-token")
''')
        terraform = bin_dir / "terraform"
        terraform.write_text(f'#!{sys.executable}\n' + '''import hashlib,json,os,sys
from pathlib import Path
args = sys.argv[1:]
assert args[0] == "-chdir=terraform/stacks/pve-lab-k3s"
stack = Path(args[0].split("=",1)[1])
saved = stack / "stage-a.tfplan"
action = args[1]
assert not any("synthetic-" in arg for arg in args)
if action != "init":
    assert os.environ["PROXMOX_VE_API_TOKEN"] == "test@pve!offline=synthetic-not-a-credential"
    assert not any(k.startswith("INFISICAL_") for k in os.environ)
with open(os.environ["TRACE"], "a") as out:
    out.write(json.dumps([action,args,hashlib.sha256((stack/"terraform.tfvars").read_bytes()).hexdigest()])+"\\n")
if action == "init":
    assert not saved.exists()
    sys.exit(int(os.environ.get("INIT_FAILURE", "0")))
if action == "plan":
    assert args[2:] == ["-input=false", "-out=stage-a.tfplan"]
    saved.write_text("synthetic reviewed plan")
    sys.exit(int(os.environ.get("PLAN_FAILURE", "0")))
assert action == "apply" and args[2:] == ["-input=false", "stage-a.tfplan"]
assert saved.read_text() == "synthetic reviewed plan"
sys.exit(int(os.environ.get("APPLY_FAILURE", "0")))
''')
        infisical = bin_dir / "infisical"
        infisical.write_text(f'#!{sys.executable}\n' + '''import os,sys
args = sys.argv[1:]
assert args[:2] == ["run", "--silent"]
assert args[args.index("--projectId")+1] == "offline-project"
assert args[args.index("--env")+1] == "dev"
assert os.environ["INFISICAL_TOKEN"] == "synthetic-session-token"
assert "PROXMOX_VE_API_TOKEN" not in os.environ
assert "INFISICAL_CLIENT_SECRET" not in os.environ
assert not any("synthetic-" in arg for arg in args)
if os.environ.get("READ_FAILURE"): sys.exit(1)
env = os.environ.copy()
if not env.get("MISSING_EXPORT"):
    env["PROXMOX_VE_API_TOKEN"] = "test@pve!offline=synthetic-not-a-credential"
command = args[args.index("--")+1:]
os.execvpe(command[0], command, env)
''')
        for file in (terraform, infisical):
            file.chmod(0o700)
        env = {"PATH": str(bin_dir), "HOME": directory,
               "PYTHONPATH": directory, "TRACE": str(trace),
               "INFISICAL_CLIENT_ID": "synthetic-id", "INFISICAL_CLIENT_SECRET": "synthetic-client-secret",
               "PROXMOX_VE_API_TOKEN": TOKEN}

        def run(source="private", target="plan", extra=None, approved=True, success=True):
            trace.unlink(missing_ok=True)
            command = [shutil.which("make"), f"stage-a-{target}", "INFISICAL_PROJECT_ID=offline-project",
                       "INFISICAL_DOMAIN=https://secrets.invalid"]
            if source is not None:
                command += [f"STAGE_A_INPUT_SOURCE={source}"]
            if approved:
                command += ["STAGE_A_ALLOCATION_REVIEWED=yes", "STAGE_A_APPLY_APPROVED=yes"]
                if target == "apply":
                    command += ["STAGE_A_PLAN_SHA256=" + hashlib.sha256(b"synthetic reviewed plan").hexdigest()]
            result = subprocess.run(command, cwd=base, env={**env, **(extra or {})}, capture_output=True, text=True)
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            output = result.stdout + result.stderr
            for secret in (TOKEN, "synthetic-id", "synthetic-client-secret", "synthetic-session-token"):
                assert secret not in output
            return [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []

        private = run(extra={"INFISICAL_CLIENT_ID": "", "INFISICAL_CLIENT_SECRET": ""})
        assert [r[0] for r in private] == ["init", "plan"]
        run(target="apply", extra={"INFISICAL_CLIENT_ID": "", "INFISICAL_CLIENT_SECRET": ""})
        assert not saved.exists()
        assert run("infisical") == private  # Same root, argv, native inputs and provider identity.
        run("infisical", target="apply")
        assert not saved.exists()
        for source in (None, "", "unknown", "private infisical"):
            assert not run(source, success=False)
        for extra in ({"PROXMOX_VE_API_TOKEN": ""}, {"PROXMOX_VE_API_TOKEN": "malformed"},
                      {"PROXMOX_VE_PASSWORD": "synthetic-password"}, {"TF_CLI_ARGS": "-lock=false"},
                      {"TF_LOG": "DEBUG"}, {"TF_WORKSPACE": "other"}):
            assert not run(extra=extra, success=False)
        assert not run("infisical", extra={"INFISICAL_CLIENT_SECRET": ""}, success=False)
        infisical.rename(bin_dir / "disabled-infisical")
        assert not run("infisical", success=False)
        assert run("private") == private
        (bin_dir / "disabled-infisical").rename(infisical)
        for source in ("private", "infisical"):
            for target in ("plan", "apply"):
                assert not run(source, target, approved=False, success=False)
            for extra in ({"INIT_FAILURE": "1"}, {"PLAN_FAILURE": "1"}):
                saved.write_text("stale plan")
                run(source, extra=extra, success=False)
                assert not saved.exists()
            for extra in ({}, {"APPLY_FAILURE": "1"}):
                saved.write_text("tampered plan" if not extra else "synthetic reviewed plan")
                result = run(source, "apply", extra=extra, success=False)
                assert saved.exists()
                assert bool(result) == bool(extra)
        for failure in ("LOGIN_FAILURE", "READ_FAILURE", "MISSING_EXPORT"):
            rows = run("infisical", extra={failure: "1"}, success=False)
            assert [r[0] for r in rows] == ["init"]  # No provider plan, no ambient-token fallback.
            assert not saved.exists()
        (base / "infisical_sdk.py").write_text('raise ImportError("must not be loaded for private mode")\n')
        assert run("private") == private
        assert not run("infisical", success=False)
        profile.unlink()
        assert not run(success=False)
    print("PASS: explicit sources, equivalent inputs, no fallback/leaks, missing auth, plan cleanup and approval/hash guards")


if __name__ == "__main__":
    main()
