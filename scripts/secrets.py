#!/usr/bin/env python3
"""Secret store entry point for the workstation (ADR-004): one explicit store, no default, no fallback.

  scripts/secrets.py run /pve-management [/k3s ...] -- <command>   run a command with those paths' secrets
  scripts/secrets.py set /headlamp                                 create or update KEY=VALUE lines from stdin
  scripts/secrets.py inventory                                     folders and key names of the active store
  scripts/secrets.py migrate [--dry-run]                           copy every Infisical secret into Phase, verify
  scripts/secrets.py verify                                        compare Infisical and Phase by value digest
  scripts/secrets.py recovery-export                               age-encrypted copy of the bootstrap paths

The store is SECRET_STORE or the one-word file .local/secret-store: infisical | phase | recovery.
"recovery" reads the age bundle written by recovery-export; it exists for the day Phase itself is down
(Phase runs on k3s and needs the bootstrap paths to be rebuilt). Values are never printed.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORES = ("infisical", "phase", "recovery")
PATH_RE = re.compile(r"^/([a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*)?$")
# Everything needed to rebuild the platform below Phase, and Phase itself.
BOOTSTRAP_PATHS = ("/pve-management", "/postgresql", "/k3s", "/phase")
INFISICAL_ENV = os.environ.get("INFISICAL_ENV", "dev")
PHASE_APP = os.environ.get("PHASE_APP", "homelab-iac")
PHASE_ENV = os.environ.get("PHASE_ENV", "development")
PHASE_HOST = os.environ.get("PHASE_HOST", "https://phase.192.168.0.40.sslip.io")
BUNDLE = Path(os.environ.get("SECRETS_RECOVERY_BUNDLE", ROOT / ".local/recovery/secrets.json.age"))


def die(message):
    print(f"secrets: {message}", file=sys.stderr)
    sys.exit(2)


def active_store():
    setting = ROOT / ".local/secret-store"
    store = os.environ.get("SECRET_STORE") or (setting.read_text().strip() if setting.exists() else "")
    if store not in STORES:
        die("set SECRET_STORE or .local/secret-store to one of: " + ", ".join(STORES) + " (no default, no fallback)")
    return store


def check_paths(paths):
    for path in paths:
        if not PATH_RE.match(path):
            die(f"invalid path {path!r}: use /name")
    return list(paths)


def output(argv, env=None):
    result = subprocess.run(argv, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        die(f"{argv[0]} {argv[1] if len(argv) > 1 else ''} failed (exit {result.returncode}); its output is withheld")
    return result.stdout


def phase_env():
    return {**os.environ, "PHASE_HOST": PHASE_HOST}


def infisical_read(path):
    rows = json.loads(output(["infisical", "secrets", "--env", INFISICAL_ENV, "--path", path, "-o", "json"]) or "[]")
    return {row["secretKey"]: row["secretValue"] for row in rows or []}


def infisical_folders(path="/"):
    rows = json.loads(output(["infisical", "secrets", "folders", "get", "--env", INFISICAL_ENV, "--path", path, "-o", "json"]) or "[]")
    found = []
    for row in rows or []:
        child = path.rstrip("/") + "/" + row["folderName"]
        found += [child] + infisical_folders(child)
    return found


def phase_read(path):
    data = output(["phase", "secrets", "export", "--app", PHASE_APP, "--env", PHASE_ENV, "--path", path, "--format", "json"],
                  env=phase_env())
    return {key: str(value) for key, value in json.loads(data or "{}").items()}


def recovery_read():
    identity = os.environ.get("AGE_IDENTITY_FILE")
    if not identity or not Path(identity).is_file():
        die("set AGE_IDENTITY_FILE to the operator's age identity to open the recovery bundle")
    if not BUNDLE.is_file():
        die(f"no recovery bundle at {BUNDLE}")
    return json.loads(output(["age", "--decrypt", "--identity", identity, str(BUNDLE)]))


def read(store, path):
    if store == "infisical":
        return infisical_read(path)
    if store == "phase":
        return phase_read(path)
    bundle = recovery_read()
    if path not in bundle:
        die(f"{path} is not in the recovery bundle (bootstrap paths only)")
    return bundle[path]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def cmd_run(args):
    if "--" not in args:
        die("usage: secrets.py run /path [/path ...] -- <command>")
    paths, command = check_paths(args[:args.index("--")]), args[args.index("--") + 1:]
    if not paths or not command:
        die("usage: secrets.py run /path [/path ...] -- <command>")
    store = active_store()
    env = dict(os.environ)
    for path in paths:
        values = read(store, path)
        if not values:
            die(f"{store}: no secrets at {path}")
        env.update(values)
    os.execvpe(command[0], command, env)


def cmd_inventory(_args):
    store = active_store()
    if store != "infisical":
        die("inventory lists the Infisical side; use `phase secrets list` for Phase")
    for path in ["/"] + infisical_folders():
        keys = sorted(infisical_read(path))
        print(f"{path}  {len(keys)}  {', '.join(keys)}")


def dotenv_line(key, value):
    if "\n" in value or "'" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'{key}="{escaped}"\n'
    return f"{key}='{value}'\n"


def compare(paths):
    clean = True
    for path in paths:
        source, target = infisical_read(path), phase_read(path)
        missing = sorted(set(source) - set(target))
        different = sorted(k for k in set(source) & set(target) if digest(source[k]) != digest(target[k]))
        state = "ok" if not missing and not different else "MISMATCH"
        print(f"{path}  infisical={len(source)} phase={len(target)}  {state}"
              + (f"  missing: {', '.join(missing)}" if missing else "")
              + (f"  different: {', '.join(different)}" if different else ""))
        clean = clean and state == "ok"
    return clean


def cmd_migrate(args):
    dry_run = "--dry-run" in args
    paths = [p for p in ["/"] + infisical_folders() if infisical_read(p)]
    for path in paths:
        source = infisical_read(path)
        print(f"{path}  {len(source)} keys{'  (dry run)' if dry_run else ''}")
        if dry_run:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".env", dir=ROOT / ".local", delete=True) as handle:
            os.chmod(handle.name, 0o600)
            handle.writelines(dotenv_line(key, value) for key, value in sorted(source.items()))
            handle.flush()
            output(["phase", "secrets", "import", handle.name, "--app", PHASE_APP, "--env", PHASE_ENV, "--path", path],
                   env=phase_env())
    if not dry_run and not compare(paths):
        die("the copy differs from the source: fix the listed keys before switching the store")


def cmd_set(args):
    """Create or update secrets at one path from KEY=VALUE lines on standard input."""
    if len(args) != 1:
        die("usage: secrets.py set /path  (KEY=VALUE lines on standard input)")
    path, store = check_paths(args)[0], active_store()
    if store == "recovery":
        die("the recovery bundle is read-only; write to the live store and export again")
    pairs = dict(line.split("=", 1) for line in sys.stdin.read().splitlines() if "=" in line)
    if not pairs or not all(re.fullmatch(r"[A-Z][A-Z0-9_]*", key) and value for key, value in pairs.items()):
        die("expected KEY=VALUE lines with upper-case keys and non-empty values")
    (ROOT / ".local").mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".env", dir=ROOT / ".local", delete=True) as handle:
        os.chmod(handle.name, 0o600)
        handle.writelines(dotenv_line(key, value) for key, value in sorted(pairs.items()))
        handle.flush()
        if store == "infisical":
            parent, _, name = path.rpartition("/")
            subprocess.run(["infisical", "secrets", "folders", "create", "--env", INFISICAL_ENV, "--path", parent or "/",
                            "--name", name], capture_output=True)  # exists already on every run but the first
            output(["infisical", "secrets", "set", "--env", INFISICAL_ENV, "--path", path, "--file", handle.name])
        else:
            output(["phase", "secrets", "import", handle.name, "--app", PHASE_APP, "--env", PHASE_ENV, "--path", path],
                   env=phase_env())
    stored = read(store, path)
    wrong = sorted(key for key, value in pairs.items() if digest(stored.get(key, "")) != digest(value))
    if wrong:
        die(f"{store}: stored value differs for {', '.join(wrong)}")
    print(f"{store} {path}: stored {', '.join(sorted(pairs))}")


def cmd_verify(_args):
    paths = [p for p in ["/"] + infisical_folders() if infisical_read(p)]
    if not compare(paths):
        sys.exit(1)


def cmd_recovery_export(_args):
    recipients = os.environ.get("AGE_RECIPIENTS_FILE")
    if not recipients or not Path(recipients).is_file():
        die("set AGE_RECIPIENTS_FILE to the operator's public age recipients file")
    store = active_store()
    if store == "recovery":
        die("export reads the live store (infisical or phase), not the bundle itself")
    bundle = {path: read(store, path) for path in BOOTSTRAP_PATHS}
    empty = [path for path, values in bundle.items() if not values]
    if empty:
        die(f"{store}: no secrets at {', '.join(empty)}; refusing to write an incomplete bundle")
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["age", "--encrypt", "--recipients-file", recipients, "--output", str(BUNDLE)],
                            input=json.dumps(bundle), text=True, capture_output=True)
    if result.returncode != 0:
        die("age failed to encrypt the bundle")
    os.chmod(BUNDLE, 0o600)
    for path, values in bundle.items():
        print(f"{path}  {len(values)} keys")
    print(f"wrote {BUNDLE} from {store}; keep a copy and the age identity outside this infrastructure")


COMMANDS = {"run": cmd_run, "set": cmd_set, "inventory": cmd_inventory, "migrate": cmd_migrate, "verify": cmd_verify,
            "recovery-export": cmd_recovery_export}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        die("usage: secrets.py " + " | ".join(COMMANDS))
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
