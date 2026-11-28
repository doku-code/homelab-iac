#!/usr/bin/env python3
"""Installs the Charcoal Titanium theme into the Forgejo app of the NAS (TASK-039). Re-runnable.

  1. writes theme-charcoal-titanium.css and the mark (img/logo.svg, favicon.svg, favicon.png) into Forgejo's custom
     directory; nothing of Forgejo's own is replaced, custom files only take precedence over them
  2. adds FORGEJO__ui__THEMES and FORGEJO__ui__DEFAULT_THEME to the app's extra environment variables, which
     redeploys the app (Forgejo restarts; its data, database and repositories are host paths and are not touched)
  3. writes contributions.sh into custom/scripts and keeps one cron job on the NAS that runs it inside Forgejo's
     container every ten minutes (dates and counts only), so the grid of the profile page follows the commits
     instead of the last time someone ran a generator by hand. The operator's own files are left as they are.

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
# Files of the custom directory: (path under custom/, file beside this script).
FILES = [("public/assets/css/theme-charcoal-titanium.css", "theme-charcoal-titanium.css"), ("public/assets/img/logo.svg", "img/logo.svg"),
         ("public/assets/img/favicon.svg", "img/favicon.svg"), ("public/assets/img/favicon.png", "img/favicon.png"),
         ("scripts/contributions.sh", "contributions.sh")]
CRON = {"description": "Forgejo: contribution counts of the profile page (homelab-iac services/forgejo)", "user": "root", "enabled": True,
        # Output hidden: a job that fails every ten minutes must not mail the NAS's alerts; "generated_at" of the file tells its age.
        "stdout": True, "stderr": True, "schedule": {"minute": "*/10", "hour": "*", "dom": "*", "month": "*", "dow": "*"},
        # One run at a time: a run that outlasts ten minutes is not joined by a second one.
        "command": ("flock -n /run/forgejo-contributions.lock docker exec "
                    "$(docker ps -q -f label=com.docker.compose.project=ix-forgejo -f label=com.docker.compose.service=forgejo) "
                    "sh /var/lib/gitea/custom/scripts/contributions.sh")}
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
    custom = f"{directory}/custom"
    folders = {name.rsplit("/", 1)[0] for name, _ in FILES}
    missing = sorted(folder for folder in folders
                     if folder.rpartition("/")[2] not in {entry["name"] for entry in session.call("filesystem.listdir", f"{custom}/{folder.rpartition('/')[0]}".rstrip("/"))})
    jobs = [job for job in session.call("cronjob.query") if job["description"] == CRON["description"]]
    cron_same = bool(jobs) and all(jobs[0][key] == value for key, value in CRON.items())

    envs = config[APP].get("additional_envs") or []
    kept = [env for env in envs if env["name"] not in WANTED]
    wanted = kept if undo else kept + [{"name": name, "value": value} for name, value in WANTED.items()]
    same = sorted(map(str, envs)) == sorted(map(str, wanted))
    print(f"files under {custom}: {', '.join(name for name, _ in FILES)}: written" if not undo else "files: left in place")
    print(f"cron job on the NAS: {'unchanged' if cron_same and not undo else 'removed' if undo else 'updated' if jobs else 'created'}: {CRON['command']}")
    print(f"environment of the app: {'unchanged' if same else 'changes (' + ', '.join(WANTED) + '), the app is redeployed'}")
    if not approved:
        print("nothing done: approve with FORGEJO_THEME_APPROVED=yes")
        return

    if not undo:
        run_as = config["run_as"]
        for folder in missing:
            session.call("filesystem.mkdir", {"path": f"{custom}/{folder}", "options": {"mode": "755", "raise_chmod_error": False}})
        for name, source in FILES:
            session.call("filesystem.file_receive", f"{custom}/{name}", base64.b64encode((THEME.parent / source).read_bytes()).decode(),
                         {"mode": 0o755 if name.endswith(".sh") else 0o644, "uid": run_as["user"], "gid": run_as["group"]})
        print("files written")
        if not jobs:
            session.call("cronjob.create", CRON)
        elif not cron_same:
            session.call("cronjob.update", jobs[0]["id"], CRON)
        (job,) = [job for job in session.call("cronjob.query") if job["description"] == CRON["description"]]
        session.call("cronjob.run", job["id"])  # once now, without waiting for the next tenth minute
        print("cron job in place, run once")
    else:
        for job in jobs:
            session.call("cronjob.delete", job["id"])
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
