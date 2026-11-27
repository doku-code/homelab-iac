#!/usr/bin/env python3
"""The apps of the NAS as files (TASK-037): services/truenas/apps/<name>.yaml is what TrueNAS should run.

  export <app>   write the file from what TrueNAS runs now; values that look like secrets become ${NAME}
                 placeholders and go to the secret store (path /truenas), never to the file or the screen
  plan [app…]    compare the files with TrueNAS; exit 2 when something would change
  apply [app…]   make TrueNAS match the files (TRUENAS_APPS_APPROVED=yes); an app is redeployed when it changes

A file describes either a custom app (kind: custom, a Compose project) or a catalog app (kind: catalog, its
catalog version and the values of its form). Installing or deleting an app is not done here: an app that has no
file is reported and left alone. Placeholders are filled from the environment (scripts/secrets.py run /truenas).
Environment: TRUENAS_API_KEY, TRUENAS_URL and TRUENAS_VERIFY as for services/observability/truenas-exporter.py.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "services/truenas/apps"
SECRET_NAME = re.compile(r"key|pass|secret|token|claim|credential", re.I)
PLACEHOLDER = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


def die(message, code=1):
    print(f"truenas-apps: {message}", file=sys.stderr)
    sys.exit(code)


def connect():
    """The WebSocket client lives with the exporter, which must stay a single file."""
    os.environ.setdefault("TRUENAS_VERIFY", "false")  # the certificate TrueNAS was installed with
    spec = importlib.util.spec_from_file_location("truenas_exporter", ROOT / "services/observability/truenas-exporter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not os.environ.get("TRUENAS_API_KEY"):
        die("set TRUENAS_API_KEY in the environment (scripts/secrets.py run /truenas -- …)")
    return module.connect()


def live_config(session, name):
    return {key: value for key, value in session.call("app.config", name).items() if not key.startswith("ix_")}


def variable(app, key):
    return re.sub(r"[^A-Z0-9]+", "_", f"{app}_{key}".upper()).strip("_")


def extract_secrets(app, value, name="", found=None):
    """Returns the value with secrets replaced by placeholders, collecting them in found."""
    if isinstance(value, dict):
        return {key: extract_secrets(app, item, key, found) for key, item in value.items()}
    if isinstance(value, list):
        return [extract_secrets(app, item, name, found) for item in value]
    if isinstance(value, str):
        key, sep, item = value.partition("=")
        if name == "environment" and sep and SECRET_NAME.search(key) and item:
            found[variable(app, key)] = item
            return f"{key}=${{{variable(app, key)}}}"
        if SECRET_NAME.search(name) and value:
            found[variable(app, name)] = value
            return f"${{{variable(app, name)}}}"
    return value


def render(value, missing):
    if isinstance(value, dict):
        return {key: render(item, missing) for key, item in value.items()}
    if isinstance(value, list):
        return [render(item, missing) for item in value]
    if isinstance(value, str):
        def fill(match):
            if match.group(1) not in os.environ:
                missing.add(match.group(1))
            return os.environ.get(match.group(1), "")
        return PLACEHOLDER.sub(fill, value)
    return value


def placeholders(value):
    return set(PLACEHOLDER.findall(json.dumps(value)))


def differences(wanted, live, path=""):
    """Paths that differ, with both sides; a value under a secret name is never shown."""
    if isinstance(wanted, dict) and isinstance(live, dict):
        for key in sorted(set(wanted) | set(live)):
            yield from differences(wanted.get(key), live.get(key), f"{path}.{key}" if path else key)
    elif isinstance(wanted, list) and isinstance(live, list) and len(wanted) == len(live):
        for index, (one, other) in enumerate(zip(wanted, live)):
            yield from differences(one, other, f"{path}[{index}]")
    elif wanted != live:
        yield path, wanted, live


def shown(path, value, secret_paths):
    if path in secret_paths:
        return "<secret>"
    text = json.dumps(value)
    return text if len(text) <= 100 else text[:97] + "…"


def secret_paths(template, path=""):
    if isinstance(template, dict):
        for key, item in template.items():
            yield from secret_paths(item, f"{path}.{key}" if path else key)
    elif isinstance(template, list):
        for index, item in enumerate(template):
            yield from secret_paths(item, f"{path}[{index}]")
    elif isinstance(template, str) and PLACEHOLDER.search(template):
        yield path


def load(names):
    files = sorted(APPS.glob("*.yaml"))
    documents = {path.stem: yaml.safe_load(path.read_text()) for path in files}
    unknown = set(names) - set(documents)
    if unknown:
        die(f"no file for {', '.join(sorted(unknown))} in {APPS.relative_to(ROOT)}")
    return {name: document for name, document in documents.items() if not names or name in names}


def body(document):
    return document["compose"] if document["kind"] == "custom" else document["values"]


def compare(session, documents):
    apps = {app["name"]: app for app in session.call("app.query")}
    changes, missing = {}, set()
    for name, document in documents.items():
        if name not in apps:
            die(f"{name}: not installed on TrueNAS; installing an app is done in its interface, then exported")
        wanted = render(body(document), missing)
        found = list(differences(wanted, live_config(session, name)))
        version = None
        if document["kind"] == "catalog" and document["version"] != apps[name]["version"]:
            version = (apps[name]["version"], document["version"])
        hidden = set(secret_paths(body(document)))
        print(f"{name}: " + ("no change" if not found and not version else f"{len(found) + bool(version)} to change"))
        if version:
            print(f"  catalog version: {version[0]} -> {version[1]}")
        for path, one, other in found:
            print(f"  {path}: {shown(path, other, hidden)} -> {shown(path, one, hidden)}")
        if found or version:
            changes[name] = (wanted, bool(found), version)
    for name in sorted(set(apps) - {path.stem for path in APPS.glob("*.yaml")}):
        print(f"{name}: runs on TrueNAS without a file here (left alone)")
    if missing:
        die(f"not in the environment: {', '.join(sorted(missing))} (store path /truenas)")
    return changes


def wait(session, job, what):
    for _ in range(360):
        (state,) = session.call("core.get_jobs", [["id", "=", job]])
        if state["state"] in ("SUCCESS", "FAILED", "ABORTED"):
            if state["state"] != "SUCCESS":
                die(f"{what}: {state['state']}: {(state.get('error') or '')[:400]}")
            return
        time.sleep(5)
    die(f"{what}: still running after 30 minutes")


def cmd_export(names):
    if len(names) != 1:
        die("usage: truenas-apps.py export <app>")
    (name,) = names
    session = connect()
    (app,) = [a for a in session.call("app.query") if a["name"] == name] or die(f"{name}: not installed on TrueNAS")
    found = {}
    config = extract_secrets(name, live_config(session, name), found=found)
    session.close()
    if app["custom_app"]:
        document = {"name": name, "kind": "custom", "compose": config}
    else:
        document = {"name": name, "kind": "catalog", "train": app["metadata"]["train"], "version": app["version"], "values": config}
    APPS.mkdir(parents=True, exist_ok=True)
    (APPS / f"{name}.yaml").write_text(yaml.safe_dump(document, sort_keys=False, width=110))
    if found:
        lines = "".join(f"{key}={value}\n" for key, value in sorted(found.items()))
        subprocess.run([str(ROOT / "scripts/secrets.py"), "set", "/truenas"], input=lines, text=True, check=True, stdout=subprocess.DEVNULL)
    print(f"{name}: written to {(APPS / (name + '.yaml')).relative_to(ROOT)}; in the store: {', '.join(sorted(found)) or 'nothing'}")


def cmd_plan(names):
    session = connect()
    changes = compare(session, load(names))
    session.close()
    sys.exit(2 if changes else 0)


def cmd_apply(names):
    if os.environ.get("TRUENAS_APPS_APPROVED") != "yes":
        die("read the plan first, then approve with TRUENAS_APPS_APPROVED=yes")
    session = connect()
    documents = load(names)
    for name, (wanted, changed, version) in compare(session, documents).items():
        if version:
            wait(session, session.call("app.upgrade", name, {"app_version": version[1]}), f"{name}: upgrade")
            print(f"{name}: catalog version {version[1]}")
        if changed:
            payload = {"custom_compose_config": wanted} if documents[name]["kind"] == "custom" else {"values": wanted}
            wait(session, session.call("app.update", name, payload), f"{name}: update")
            print(f"{name}: updated")
    left = compare(session, documents)
    session.close()
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    commands = {"export": cmd_export, "plan": cmd_plan, "apply": cmd_apply}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        die("usage: truenas-apps.py export <app> | plan [app…] | apply [app…]")
    commands[sys.argv[1]](sys.argv[2:])
