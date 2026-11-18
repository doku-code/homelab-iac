#!/usr/bin/env python3
"""Authentik from the workstation (M014, ADR-017).

  scripts/authentik-admin.py status [--apply]   blueprints of this repository and the applications they declare;
                                                with --apply, blueprints that are not applied yet are applied again
                                                and the command waits for them

What Authentik holds is declared in services/authentik/blueprints; this tool creates and deletes nothing itself.
The API token of the first administrator comes from the environment only (AUTHENTIK_BOOTSTRAP_TOKEN, store path
/authentik) and is never printed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ.get("AUTHENTIK_URL", "https://auth.doku-lab.net")
PREFIX = "Homelab - "  # metadata.name of every blueprint of this repository


def die(message):
    print(f"authentik-admin: {message}", file=sys.stderr)
    sys.exit(2)


def call(method, path, token, body=None, expect=(200, 201, 204)):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"{URL}/api/v3{path}", data=data, method=method,
                                     headers={"Accept": "application/json", "Authorization": f"Bearer {token}"})
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        return None, str(error)
    if expect is not None and status not in expect:
        die(f"{method} {path}: HTTP {status} {text[:300]}")
    try:
        return status, json.loads(text) if text else None
    except ValueError:
        return status, text


def listing(path, token, **query):
    query = {"page_size": 200, **query}
    _, page = call("GET", f"{path}?{urllib.parse.urlencode(query)}", token)
    return page["results"]


def wait_for_api(token, minutes=10):
    for _ in range(minutes * 12):
        status, _ = call("GET", "/root/config/", token, expect=None)
        if status == 200:
            return
        if status in (401, 403):
            die("the API refuses AUTHENTIK_BOOTSTRAP_TOKEN (Authentik reads it at its first start only)")
        time.sleep(5)
    die(f"{URL} did not answer within {minutes} minutes")


def blueprints(token):
    return sorted((b for b in listing("/managed/blueprints/", token) if b["name"].startswith(PREFIX)), key=lambda b: b["name"])


def cmd_status(args):
    token = os.environ.get("AUTHENTIK_BOOTSTRAP_TOKEN") or die("set AUTHENTIK_BOOTSTRAP_TOKEN in the environment (store path /authentik)")
    apply = "--apply" in args
    wait_for_api(token)
    expected = int(os.environ.get("AUTHENTIK_EXPECTED_BLUEPRINTS", "0"))
    if apply:
        # Applying again is harmless and makes Authentik read the files as they are now.
        for blueprint in blueprints(token):
            call("POST", f"/managed/blueprints/{blueprint['pk']}/apply/", token, expect=None)
        time.sleep(10)
    for attempt in range(40 if apply else 1):
        found = blueprints(token)
        pending = [b for b in found if b["status"] != "successful"]
        if not pending and len(found) >= expected:
            break
        if apply:
            # A blueprint that ran before what it refers to existed (first start) is simply applied again.
            for blueprint in pending:
                call("POST", f"/managed/blueprints/{blueprint['pk']}/apply/", token, expect=None)
            time.sleep(15)
    for blueprint in found:
        print(f"blueprint  {blueprint['status']:<11} {blueprint['name']}")
    groups = {g["pk"]: g["name"] for g in listing("/core/groups/", token)}
    for application in sorted(listing("/core/applications/", token, superuser_full_list="true"), key=lambda a: a["slug"]):
        bindings = listing("/policies/bindings/", token, target=application["pk"])
        allowed = sorted(groups.get(b["group"], "?") for b in bindings if b.get("group")) or ["everyone"]
        provider = (application.get("provider_obj") or {}).get("verbose_name", "no provider")
        print(f"application {application['slug']:<12} {provider:<24} open to: {', '.join(allowed)}")
    if pending or len(found) < expected:
        die(f"{len(pending)} blueprint(s) not applied, {len(found)} of {expected} expected found; see System > Blueprints in Authentik")


def main(argv):
    if not argv or argv[0] != "status":
        die("usage: authentik-admin.py status [--apply]")
    cmd_status(argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
