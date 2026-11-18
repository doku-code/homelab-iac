#!/usr/bin/env python3
"""Windmill administration from the workstation (M009, ADR-005).

  scripts/windmill-admin.py bootstrap   replace the built-in administrator password, create the workspace and the
                                        automation token, give the workspace its read-only NetBox token
  scripts/windmill-admin.py push        publish the scripts of windmill/ (create or update; never delete)
  scripts/windmill-admin.py run <path> [json arguments]   run one script and print its result

Credentials come from the environment only and are never printed: WINDMILL_ADMIN_PASSWORD and NETBOX_READ_TOKEN
(bootstrap), WINDMILL_TOKEN (push, run). Store paths /windmill and /netbox.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("WINDMILL_URL", "https://windmill.doku-lab.net")
WORKSPACE = "homelab"
ADMIN = "admin@windmill.dev"
BUILT_IN_PASSWORD = "changeme"  # public default of every new Windmill; bootstrap replaces it
LANGUAGES = {".py": "python3"}


def die(message):
    print(f"windmill-admin: {message}", file=sys.stderr)
    sys.exit(2)


def call(method, path, token=None, body=None, expect=(200, 201)):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"{URL}/api{path}", data=data, method=method, headers={"Accept": "application/json"})
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode()
    if expect is not None and status not in expect:
        # Windmill's error bodies are short messages; they do not echo the request.
        die(f"{method} {path}: HTTP {status} {text[:300]}")
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def login(password):
    status, token = call("POST", "/auth/login", body={"email": ADMIN, "password": password}, expect=None)
    return token if status == 200 and isinstance(token, str) else None


def cmd_bootstrap():
    password = os.environ.get("WINDMILL_ADMIN_PASSWORD") or die("set WINDMILL_ADMIN_PASSWORD in the environment (store path /windmill)")
    netbox_token = os.environ.get("NETBOX_READ_TOKEN") or die("set NETBOX_READ_TOKEN in the environment (store path /netbox)")
    if len(password) < 16 or password == BUILT_IN_PASSWORD:
        die("WINDMILL_ADMIN_PASSWORD must be a real password of at least 16 characters")
    session = login(password)
    if session is None:
        session = login(BUILT_IN_PASSWORD) or die("neither the stored password nor the built-in one is accepted")
        call("POST", "/users/setpassword", session, {"password": password})
        session = login(password) or die("the new password is not accepted")
        print(f"{ADMIN}: built-in password replaced")
    else:
        print(f"{ADMIN}: password already set")
    if login(BUILT_IN_PASSWORD) is not None:
        die("the built-in password still works")

    _, exists = call("POST", "/workspaces/exists", session, {"id": WORKSPACE})
    if exists is True:
        print(f"workspace {WORKSPACE}: exists")
    else:
        call("POST", "/workspaces/create", session, {"id": WORKSPACE, "name": WORKSPACE})
        print(f"workspace {WORKSPACE}: created")

    status, _ = call("GET", f"/w/{WORKSPACE}/folders/get/netbox", session, expect=None)
    if status != 200:
        call("POST", f"/w/{WORKSPACE}/folders/create", session, {"name": "netbox"})
    path = "f/netbox/read_token"
    description = "Read-only NetBox API token of the account automation-read (written by make windmill-bootstrap)"
    status, _ = call("GET", f"/w/{WORKSPACE}/variables/get/{path}", session, expect=None)
    if status == 200:
        call("POST", f"/w/{WORKSPACE}/variables/update/{path}", session, {"value": netbox_token, "is_secret": True, "description": description})
        print(f"variable {path}: updated")
    else:
        call("POST", f"/w/{WORKSPACE}/variables/create", session, {"path": path, "value": netbox_token, "is_secret": True, "description": description})
        print(f"variable {path}: created")

    if os.environ.get("WINDMILL_TOKEN"):
        print("automation token: WINDMILL_TOKEN is already in the store, no new token")
        return
    _, token = call("POST", "/users/tokens/create", session, {"label": "homelab-iac workstation (store path /windmill)"})
    stored = subprocess.run([sys.executable, str(ROOT / "scripts/secrets.py"), "set", "/windmill"], input=f"WINDMILL_TOKEN={token}\n", text=True)
    if stored.returncode != 0:
        die("the token was created but not stored; delete it in Windmill (account settings) and run again")
    print("automation token: created and stored")


def local_scripts():
    """path in Windmill -> (file, metadata) for every script under windmill/."""
    found = {}
    for source in sorted((ROOT / "windmill").glob("[fu]/**/*")):
        if source.suffix in LANGUAGES:
            metadata = yaml.safe_load(source.with_suffix(".script.yaml").read_text())
            found[str(source.relative_to(ROOT / "windmill").with_suffix(""))] = (source, metadata)
    return found


def cmd_push():
    token = os.environ.get("WINDMILL_TOKEN") or die("set WINDMILL_TOKEN in the environment (store path /windmill)")
    for path, (source, metadata) in local_scripts().items():
        content = source.read_text()
        status, current = call("GET", f"/w/{WORKSPACE}/scripts/get/p/{path}", token, expect=None)
        wanted = (content, metadata["summary"], metadata["description"])
        if status == 200 and (current["content"], current["summary"], current["description"]) == wanted:
            print(f"{path}: unchanged")
            continue
        # The form (argument names, types, defaults) is derived from the signature of main().
        body = {"path": path, "summary": metadata["summary"], "description": metadata["description"], "content": content,
                "language": LANGUAGES[source.suffix], "kind": metadata.get("kind", "script"), "schema": signature_schema(content)}
        if status == 200:
            body["parent_hash"] = current["hash"]
        call("POST", f"/w/{WORKSPACE}/scripts/create", token, body)
        print(f"{path}: {'updated' if status == 200 else 'created'} ({hashlib.sha256(content.encode()).hexdigest()[:12]})")


def signature_schema(content):
    """The form of a script: the arguments of main() with their type and default (strings, integers, booleans)."""
    import ast
    main = next(node for node in ast.parse(content).body if isinstance(node, ast.FunctionDef) and node.name == "main")
    types = {"str": "string", "int": "integer", "bool": "boolean", "float": "number"}
    defaults = [None] * (len(main.args.args) - len(main.args.defaults)) + list(main.args.defaults)
    properties, required = {}, []
    for argument, default in zip(main.args.args, defaults):
        annotation = getattr(argument.annotation, "id", "str")
        properties[argument.arg] = {"type": types.get(annotation, "string"), "description": ""}
        if default is None:
            required.append(argument.arg)
        else:
            properties[argument.arg]["default"] = ast.literal_eval(default)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": properties, "required": required}


def cmd_run(args):
    if not args:
        die("usage: windmill-admin.py run <path> [json arguments]")
    token = os.environ.get("WINDMILL_TOKEN") or die("set WINDMILL_TOKEN in the environment (store path /windmill)")
    arguments = json.loads(args[1]) if len(args) > 1 else {}
    _, job = call("POST", f"/w/{WORKSPACE}/jobs/run/p/{args[0]}", token, arguments)
    for _ in range(120):
        status, result = call("GET", f"/w/{WORKSPACE}/jobs_u/completed/get_result_maybe/{job}", token, expect=None)
        if status == 200 and result.get("completed"):
            print(json.dumps(result["result"], indent=1))
            sys.exit(0 if result.get("success") else 1)
        time.sleep(2)
    die(f"job {job} did not finish within four minutes")


def main(argv):
    if not argv or argv[0] not in ("bootstrap", "push", "run"):
        die("usage: windmill-admin.py bootstrap | push | run <path> [json arguments]")
    if argv[0] == "bootstrap":
        cmd_bootstrap()
    elif argv[0] == "push":
        cmd_push()
    else:
        cmd_run(argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
