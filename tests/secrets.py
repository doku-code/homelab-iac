#!/usr/bin/env python3
"""Offline tests for scripts/secrets.py: explicit store, run, migration with digest verification, recovery bundle.

Fake `infisical` and `phase` commands serve synthetic values from files; `age` is the real tool with a
throw-away key. Nothing reaches a real store.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/secrets.py"
SOURCE = {
    "/": {"ROOT_KEY": "synthetic-root"},
    "/k3s": {"K3S_TOKEN": "synthetic-" + "a" * 20},
    "/phase": {"PHASE_SERVER_SECRET": "synthetic-server", "PHASE_SECRET_KEY": "synthetic-key"},
    "/postgresql": {"PG_SUPERUSER_PASSWORD": "synthetic pass with 'quote' and $dollar", "MULTI": "line1\nline2 \"q\""},
    "/pve-management": {"PROXMOX_VE_API_TOKEN": "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"},
}

FAKE_INFISICAL = r'''#!/usr/bin/env python3
import json, os, sys
data = json.load(open(os.environ["FAKE_SOURCE"]))
args = sys.argv[1:]
path = args[args.index("--path") + 1]
if args[:3] == ["secrets", "folders", "create"]:
    sys.exit(0)
elif args[:2] == ["secrets", "set"]:
    for line in open(args[args.index("--file") + 1]).read().splitlines():
        key, raw = line.split("=", 1)
        data.setdefault(path, {})[key] = raw[1:-1]
    json.dump(data, open(os.environ["FAKE_SOURCE"], "w"))
elif args[:3] == ["secrets", "folders", "get"]:
    names = sorted({p.split("/")[1] for p in data if p != "/"}) if path == "/" else []
    print(json.dumps([{"folderName": n, "folderPath": "/", "folderId": n} for n in names]))
elif args[0] == "secrets":
    print(json.dumps([{"secretKey": k, "secretValue": v} for k, v in data.get(path, {}).items()]))
else:
    sys.exit(3)
'''

FAKE_PHASE = r'''#!/usr/bin/env python3
import json, os, sys
store_file = os.environ["FAKE_TARGET"]
store = json.load(open(store_file)) if os.path.exists(store_file) else {}
args = sys.argv[1:]
assert os.environ["PHASE_HOST"].startswith("https://"), "the wrapper sets the host"
path = args[args.index("--path") + 1]
assert args[args.index("--app") + 1] == "homelab-iac"
if args[:2] == ["secrets", "import"]:
    assert oct(os.stat(args[2]).st_mode & 0o777) == "0o600", "the transfer file is private"
    for line in open(args[2]).read().splitlines():
        key, raw = line.split("=", 1)
        if raw.startswith("'"):
            value = raw[1:-1]
        else:
            value = raw[1:-1].replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        if os.environ.get("FAKE_MANGLE") == key:
            value += "x"
        store.setdefault(path, {})[key] = value
    json.dump(store, open(store_file, "w"))
elif args[:2] == ["secrets", "export"]:
    print(json.dumps(store.get(path, {})))
else:
    sys.exit(3)
'''


def main():
    with tempfile.TemporaryDirectory(prefix="secrets-test-") as directory:
        base = Path(directory)
        fake = base / "bin"
        fake.mkdir()
        for name, body in (("infisical", FAKE_INFISICAL), ("phase", FAKE_PHASE)):
            (fake / name).write_text(body)
            (fake / name).chmod(0o755)
        (base / "source.json").write_text(json.dumps(SOURCE))
        subprocess.run(["age-keygen", "-o", str(base / "identity.txt")], check=True, capture_output=True)
        public = subprocess.run(["age-keygen", "-y", str(base / "identity.txt")], check=True, capture_output=True, text=True).stdout
        (base / "recipients.txt").write_text(public)
        env = {"PATH": f"{fake}:{os.path.dirname(sys.executable)}:/usr/bin:/bin", "HOME": str(base),
               "FAKE_SOURCE": str(base / "source.json"), "FAKE_TARGET": str(base / "target.json"),
               "SECRETS_RECOVERY_BUNDLE": str(base / "bundle.age")}

        def run(*args, store=None, extra=None):
            return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                  env={**env, **({"SECRET_STORE": store} if store else {}), **(extra or {})})

        secrets = [v for values in SOURCE.values() for v in values.values()]

        def leaks(result):
            return any(v in result.stdout + result.stderr for v in secrets)

        show = [sys.executable, "-c", "import os; print(len(os.environ['K3S_TOKEN']), 'PROXMOX_VE_API_TOKEN' in os.environ)"]
        # No store selected: refused (the repository's .local/secret-store may exist, so force an invalid one).
        refused = run("run", "/k3s", "--", *show, store="vault")
        assert refused.returncode == 2 and "no default, no fallback" in refused.stderr
        assert run("run", "../etc", "--", *show, store="infisical").returncode == 2
        assert run("run", "/k3s", store="infisical").returncode == 2, "a command is required"
        ok = run("run", "/k3s", "/pve-management", "--", *show, store="infisical")
        assert ok.returncode == 0 and ok.stdout.strip() == "30 True", ok.stderr
        assert run("run", "/nothing", "--", *show, store="infisical").returncode == 2, "an empty path is an error"

        # set: values come from standard input, are read back and compared, and are never echoed.
        def put(store, text):
            return subprocess.run([sys.executable, str(SCRIPT), "set", "/headlamp"], input=text, capture_output=True,
                                  text=True, env={**env, "SECRET_STORE": store})

        stored = put("infisical", "HEADLAMP_ADMIN_TOKEN=synthetic-headlamp-value\n")
        assert stored.returncode == 0 and "stored HEADLAMP_ADMIN_TOKEN" in stored.stdout, stored.stderr
        assert "synthetic-headlamp-value" not in stored.stdout + stored.stderr
        assert put("infisical", "lower=x\n").returncode == 2 and put("recovery", "A=b\n").returncode == 2
        SOURCE["/headlamp"] = {"HEADLAMP_ADMIN_TOKEN": "synthetic-headlamp-value"}

        inventory = run("inventory", store="infisical")
        assert "/postgresql  2  MULTI, PG_SUPERUSER_PASSWORD" in inventory.stdout and not leaks(inventory)

        dry = run("migrate", "--dry-run", store="infisical")
        assert dry.returncode == 0 and not (base / "target.json").exists() and "/phase  2 keys  (dry run)" in dry.stdout
        # A value changed in transit is detected by digest, named by key, and fails the migration.
        bad = run("migrate", store="infisical", extra={"FAKE_MANGLE": "K3S_TOKEN"})
        assert bad.returncode == 2 and "different: K3S_TOKEN" in bad.stdout and not leaks(bad)
        good = run("migrate", store="infisical")
        assert good.returncode == 0 and "MISMATCH" not in good.stdout and not leaks(good), good.stdout + good.stderr
        assert json.loads((base / "target.json").read_text()) == SOURCE, "quotes, dollars and newlines survive"
        assert run("verify", store="infisical").returncode == 0
        from_phase = run("run", "/k3s", "/pve-management", "--", *show, store="phase")
        assert from_phase.returncode == 0 and from_phase.stdout.strip() == "30 True", from_phase.stderr

        # Recovery bundle: bootstrap paths only, encrypted to the operator's recipients, opened only with the identity.
        assert run("recovery-export", store="phase").returncode == 2, "recipients are required"
        exported = run("recovery-export", store="phase", extra={"AGE_RECIPIENTS_FILE": str(base / "recipients.txt")})
        assert exported.returncode == 0 and "/phase  2 keys" in exported.stdout and not leaks(exported), exported.stderr
        raw = (base / "bundle.age").read_bytes()
        assert raw.startswith(b"age-encryption.org/") and not any(v.encode() in raw for v in secrets)
        assert oct((base / "bundle.age").stat().st_mode & 0o777) == "0o600"
        assert run("run", "/k3s", "--", *show, store="recovery").returncode == 2, "the identity is required"
        identity = {"AGE_IDENTITY_FILE": str(base / "identity.txt")}
        recovered = run("run", "/k3s", "/pve-management", "--", *show, store="recovery", extra=identity)
        assert recovered.returncode == 0 and recovered.stdout.strip() == "30 True", recovered.stderr
        assert run("run", "/", "--", *show, store="recovery", extra=identity).returncode == 2, "only bootstrap paths are in the bundle"
        # An incomplete source never overwrites a good bundle.
        (base / "target.json").write_text(json.dumps({k: v for k, v in SOURCE.items() if k != "/phase"}))
        before = (base / "bundle.age").read_bytes()
        partial = run("recovery-export", store="phase", extra={"AGE_RECIPIENTS_FILE": str(base / "recipients.txt")})
        assert partial.returncode == 2 and (base / "bundle.age").read_bytes() == before
    print("PASS: explicit store, run from infisical/phase/recovery, migration verified by digest, "
          "age recovery bundle, no value printed")


if __name__ == "__main__":
    main()
