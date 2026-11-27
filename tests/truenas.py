#!/usr/bin/env python3
"""Offline tests of the NAS's apps as files: scripts/truenas-apps.py and services/truenas/apps (TASK-037).

No call reaches TrueNAS: the comparison, the placeholders and the masking are exercised on synthetic values, and
the committed files are checked for what must never be in them.
"""
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("truenas_apps", ROOT / "scripts/truenas-apps.py")
apps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apps)


def main():
    # Export: what looks like a secret leaves the file for a placeholder named after the app and the key.
    found = {}
    live = {"services": {"vpn": {"environment": ["TZ=America/Toronto", "WIREGUARD_PRIVATE_KEY=synthetic-value", "API_TOKEN="], "image": "example/vpn:1.2.3"}},
            "plex": {"claim_token": "synthetic-claim", "limits": {"cpus": 4}}}
    template = apps.extract_secrets("my-app", live, found=found)
    assert found == {"MY_APP_WIREGUARD_PRIVATE_KEY": "synthetic-value", "MY_APP_CLAIM_TOKEN": "synthetic-claim"}, found
    assert "synthetic" not in yaml.safe_dump(template) and template["services"]["vpn"]["environment"][2] == "API_TOKEN=", "an empty value is no secret"
    assert apps.placeholders(template) == set(found)

    # Plan: placeholders come from the environment; a missing one is named, never replaced silently.
    missing = set()
    os.environ.update(found)
    assert apps.render(template, missing) == live and not missing
    del os.environ["MY_APP_CLAIM_TOKEN"]
    apps.render(template, missing)
    assert missing == {"MY_APP_CLAIM_TOKEN"}
    os.environ.update(found)

    # Differences are listed by path, and a value at a placeholder's path is never shown.
    changed = apps.render(template, set())
    changed["services"]["vpn"]["image"] = "example/vpn:1.2.4"
    changed["services"]["vpn"]["environment"][1] = "WIREGUARD_PRIVATE_KEY=another-synthetic"
    listed = list(apps.differences(changed, live))
    assert [path for path, _, _ in listed] == ["services.vpn.environment[1]", "services.vpn.image"], listed
    hidden = set(apps.secret_paths(template))
    assert hidden == {"services.vpn.environment[1]", "plex.claim_token"}
    assert [apps.shown(path, value, hidden) for path, value, _ in listed] == ["<secret>", '"example/vpn:1.2.4"']
    assert not list(apps.differences(live, live))

    # The gates: nothing is applied without the approval, and a key is needed before any connection.
    script = [sys.executable, str(ROOT / "scripts/truenas-apps.py")]
    env = {k: v for k, v in os.environ.items() if not k.startswith("TRUENAS_")}
    refused = subprocess.run(script + ["apply"], capture_output=True, text=True, env=env)
    assert refused.returncode == 1 and "TRUENAS_APPS_APPROVED=yes" in refused.stderr
    no_key = subprocess.run(script + ["plan"], capture_output=True, text=True, env=env)
    assert no_key.returncode == 1 and "TRUENAS_API_KEY" in no_key.stderr
    source = (ROOT / "scripts/truenas-apps.py").read_text()
    called = set(re.findall(r'session\.call\("([a-z_.]+)"', source))
    assert called == {"app.query", "app.config", "app.update", "app.upgrade", "core.get_jobs"}, "no install, no delete, nothing outside the apps"

    # The committed files.
    files = sorted((ROOT / "services/truenas/apps").glob("*.yaml"))
    assert {path.stem for path in files} >= {"qbit-vpn", "plex"} and "forgejo" not in {path.stem for path in files}, "Forgejo is left alone"
    for path in files:
        document = yaml.safe_load(path.read_text())
        assert document["name"] == path.stem and document["kind"] in ("custom", "catalog")
        body = apps.body(document)
        assert not any(key.startswith("ix_") for key in body), "TrueNAS's own context is not ours to set"
        clean = {}
        apps.extract_secrets(path.stem, body, found=clean)
        assert all(apps.PLACEHOLDER.search(value) for value in clean.values()), f"{path.name}: a secret is written in the file: {sorted(clean)}"
        if document["kind"] == "catalog":
            assert re.fullmatch(r"\d+\.\d+\.\d+", document["version"]) and document["train"] in ("stable", "community", "enterprise")
        else:
            for service in body["services"].values():
                assert ":" in service["image"], "an image names its tag"
    makefile = (ROOT / "Makefile").read_text()
    assert 'test "$(TRUENAS_APPS_APPROVED)" = yes' in makefile and "truenas-apps.py plan" in makefile
    print("PASS: secrets leave the files for placeholders, differences hide them, apply is gated, only app calls, committed files hold no secret")


if __name__ == "__main__":
    main()
