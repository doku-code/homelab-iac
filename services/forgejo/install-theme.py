#!/usr/bin/env python3
"""Installs the Charcoal Titanium theme into the Forgejo app of the NAS (TASK-039). Re-runnable.

  1. writes theme-charcoal-titanium.css into Forgejo's custom directory (a new file; nothing of Forgejo's is replaced)
  2. adds FORGEJO__ui__THEMES and FORGEJO__ui__DEFAULT_THEME to the app's extra environment variables, which
     redeploys the app (Forgejo restarts; its data, database and repositories are host paths and are not touched)

Without FORGEJO_THEME_APPROVED=yes it only reports what it would do. `undo` as argument removes the two variables
(the file stays; it is inert once its name is out of the list).
Environment: TRUENAS_API_KEY as for scripts/truenas-apps.py (scripts/secrets.py run /truenas -- …).
"""
import base64
import importlib.util
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = "forgejo"
THEME = Path(__file__).with_name("theme-charcoal-titanium.css")
# Forgejo 17's own themes, then ours: THEMES replaces the list, it does not add to it.
THEMES = ("forgejo-auto,forgejo-light,forgejo-dark,gitea-auto,gitea-light,gitea-dark,"
          "forgejo-auto-deuteranopia-protanopia,forgejo-light-deuteranopia-protanopia,forgejo-dark-deuteranopia-protanopia,"
          "forgejo-auto-tritanopia,forgejo-light-tritanopia,forgejo-dark-tritanopia,charcoal-titanium")
WANTED = {"FORGEJO__ui__THEMES": THEMES, "FORGEJO__ui__DEFAULT_THEME": "charcoal-titanium"}


def connect():
    os.environ.setdefault("TRUENAS_VERIFY", "false")  # the certificate TrueNAS was installed with
    spec = importlib.util.spec_from_file_location("truenas_exporter", ROOT / "services/observability/truenas-exporter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.connect()


def main():
    undo = sys.argv[1:] == ["undo"]
    approved = os.environ.get("FORGEJO_THEME_APPROVED") == "yes"
    session = connect()
    config = {key: value for key, value in session.call("app.config", APP).items() if not key.startswith("ix_")}
    data = config["storage"]["data"]["host_path_config"]
    directory = (data.get("acl") or {}).get("path") or data["path"]
    target = f"{directory}/custom/public/assets/css/{THEME.name}"
    present = {entry["name"] for entry in session.call("filesystem.listdir", target.rsplit("/", 1)[0])}

    envs = config[APP].get("additional_envs") or []
    kept = [env for env in envs if env["name"] not in WANTED]
    wanted = kept if undo else kept + [{"name": name, "value": value} for name, value in WANTED.items()]
    same = sorted(map(str, envs)) == sorted(map(str, wanted))
    print(f"theme file {target}: {'present, rewritten' if THEME.name in present else 'new'}" if not undo else "theme file: left in place")
    print(f"environment of the app: {'unchanged' if same else 'changes (' + ', '.join(WANTED) + '), the app is redeployed'}")
    if not approved:
        print("nothing done: approve with FORGEJO_THEME_APPROVED=yes")
        return

    if not undo:
        run_as = config["run_as"]
        session.call("filesystem.file_receive", target, base64.b64encode(THEME.read_bytes()).decode(),
                     {"mode": 0o644, "uid": run_as["user"], "gid": run_as["group"]})
        print("theme file written")
    if not same:
        config[APP]["additional_envs"] = wanted
        job = session.call("app.update", APP, {"values": config})
        for _ in range(180):
            (state,) = session.call("core.get_jobs", [["id", "=", job]])
            if state["state"] in ("SUCCESS", "FAILED", "ABORTED"):
                break
            time.sleep(5)
        if state["state"] != "SUCCESS":
            sys.exit(f"app.update: {state['state']}: {(state.get('error') or '')[:400]}")
        print("app updated")
    session.close()


if __name__ == "__main__":
    main()
