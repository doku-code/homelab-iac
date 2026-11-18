#!/usr/bin/env python3
"""Generate the secrets a service needs and that the store does not hold yet (ADR-004).

  scripts/ensure-secrets.py /authentik AUTHENTIK_SECRET_KEY SSO_GRAFANA_CLIENT_SECRET ...

Every missing key gets 32 random bytes as 64 hexadecimal characters, written with `scripts/secrets.py set`.
A key that already has a value is never replaced: this creates, it does not rotate. Values are never printed.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

STORE = [sys.executable, str(Path(__file__).resolve().parent / "secrets.py")]
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
PRESENT = "import os, sys; print('\\n'.join(k for k in sys.argv[1:] if os.environ.get(k)))"


def die(message):
    print(f"ensure-secrets: {message}", file=sys.stderr)
    sys.exit(2)


def present(path, keys):
    """Keys of this path that already have a value. An empty path is not an error; an unreachable store is."""
    result = subprocess.run(STORE + ["run", path, "--", sys.executable, "-c", PRESENT, *keys], capture_output=True, text=True)
    if result.returncode == 0:
        return set(result.stdout.split())
    if f"no secrets at {path}" in result.stderr:
        return set()
    die(f"cannot read {path} (exit {result.returncode}): nothing generated, so nothing existing can be replaced")


def main(argv):
    if len(argv) < 2 or not argv[0].startswith("/"):
        die("usage: ensure-secrets.py /path KEY [KEY ...]")
    path, keys = argv[0], argv[1:]
    for key in keys:
        if not KEY_RE.match(key):
            die(f"invalid key name {key!r}")
    missing = [key for key in keys if key not in present(path, keys)]
    if not missing:
        print(f"{path}: {len(keys)} present, nothing generated")
        return
    lines = "".join(f"{key}={os.urandom(32).hex()}\n" for key in missing)
    stored = subprocess.run(STORE + ["set", path], input=lines, text=True, stdout=subprocess.DEVNULL)
    if stored.returncode != 0:
        die(f"could not store the new values at {path}")
    print(f"{path}: generated {', '.join(missing)}; {len(keys) - len(missing)} already present")


if __name__ == "__main__":
    main(sys.argv[1:])
