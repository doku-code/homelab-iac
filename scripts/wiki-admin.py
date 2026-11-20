#!/usr/bin/env python3
"""Configures the wiki through its API, so that nothing is clicked and a rebuilt wiki is the same (TASK-029).

  wiki-admin.py configure   site name, Git storage (pull-only from the branch written by wiki-export.py),
                            sign-in through Authentik; then one sync and import of the whole tree
  wiki-admin.py sync        asks the wiki to pull now instead of at its next interval
  wiki-admin.py status      what the wiki holds and how its storage is doing (read-only)

Signs in as the wiki's local administrator: WIKI_ADMIN_PASSWORD (store path /wiki). `configure` also needs
SSO_WIKI_CLIENT_SECRET (store path /authentik). Nothing secret is printed. Running `configure` again changes
only what differs.
"""
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("WIKI_URL", "https://wiki.doku-lab.net")
ADMIN = "admin@doku-lab.net"
LOCAL_STRATEGY = "5a528c4c-0a82-4ad2-96a5-2b23811e6588"  # the wiki's built-in local sign-in (backend/base.yml)
SITE = {
    "title": "Doku Lab",
    "description": "Documentation of the doku-lab homelab, generated from the homelab-iac repository",
}
# Site-wide storage settings and the Git target. The repository is public on the LAN: no credentials.
STORAGE = {"localePrefix": False, "stripLeadingH1": True, "mapReadmeToHome": True, "syncInterval": "5m"}
GIT = {
    "authType": "basic", "repoUrl": "https://git.doku-lab.net/Homelab/homelab-iac.git", "branch": "wiki",
    "syncMode": "pull", "verifySSL": True, "basicUsername": "", "basicPassword": "",
    "alwaysUseDefaultAuthor": True, "defaultName": "Wiki.js", "defaultEmail": "wiki@doku-lab.net",
}
GIT_CONTENT = ["pages"]
SSO_NAME = "Authentik"
SSO_GROUP = "Administrators"  # Authentik lets only homelab-admins in; whoever signs in administers the wiki


def sso_config(secret):
    return {
        "clientId": "wiki", "clientSecret": secret, "issuer": "https://auth.doku-lab.net/application/o/wiki/",
        "useDiscovery": True, "scopes": "openid profile email", "idClaim": "sub", "emailClaim": "email",
        "displayNameClaim": "name", "mapGroups": False,
    }


class Stop(Exception):
    pass


class Wiki:
    def __init__(self, base=BASE):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.site = None

    def call(self, method, path, body=None, expect=(200,)):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Accept": "application/json", **({"Content-Type": "application/json"} if data is not None else {})}
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=120) as response:
                status, text = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, text = error.code, error.read().decode(errors="replace")
        try:
            answer = json.loads(text) if text else None
        except ValueError:
            answer = None
        if status not in expect:
            message = answer.get("message") if isinstance(answer, dict) else text[:200]
            raise Stop(f"{method} {path.split('?')[0]}: HTTP {status} {message}")
        return answer

    def sign_in(self, password):
        self.site = self.call("GET", "/_api/sites/" + self.base.split("//")[1])["id"]
        answer = self.call("PUT", f"/_api/sites/{self.site}/auth/login",
                           {"strategyId": LOCAL_STRATEGY, "username": ADMIN, "password": password})
        if not answer.get("authenticated"):
            raise Stop(f"the wiki did not accept the local administrator ({answer.get('nextAction')})")

    def git_target(self):
        storage = self.call("GET", f"/_api/sites/{self.site}/storage")
        return storage, next(t for t in storage["targets"] if t["module"] == "git")

    def action(self, target, name):
        return self.call("POST", f"/_api/sites/{self.site}/storage/targets/{target['id']}/actions/{name}").get("message", "")

    def page_count(self):
        return int(self.call("GET", "/_api/system/info").get("pagesTotal") or 0)


def differs(current, wanted):
    return {k: v for k, v in wanted.items() if current.get(k) != v}


def configure_site(wiki):
    current = wiki.call("GET", f"/_api/sites/{wiki.site}")
    change = differs(current, SITE)
    if change:
        wiki.call("PUT", f"/_api/sites/{wiki.site}", change)
    return f"site: {'updated ' + ', '.join(change) if change else 'unchanged'}"


def configure_storage(wiki):
    storage, target = wiki.git_target()
    # The API masks nothing here but the password, which is empty: the whole configuration can be compared.
    same = (not differs(storage, STORAGE) and target["isEnabled"] and not differs(target.get("config") or {}, GIT)
            and (target.get("contentTypes") or {}).get("activeTypes") == GIT_CONTENT)
    if not same:
        wiki.call("PUT", f"/_api/sites/{wiki.site}/storage", {
            **STORAGE, "targets": [{"id": target["id"], "isEnabled": True, "contentTypes": {"activeTypes": GIT_CONTENT}, "config": GIT}]})
    return f"storage: {'unchanged' if same else 'Git target set to pull ' + GIT['branch']}"


def configure_sso(wiki, secret):
    groups = {g["name"]: g["id"] for g in wiki.call("GET", "/_api/groups")}
    wanted = {"displayName": SSO_NAME, "isEnabled": True, "registration": True, "allowedEmailRegex": "",
              "autoEnrollGroups": [groups[SSO_GROUP]], "config": sso_config(secret)}
    existing = [s for s in wiki.call("GET", "/_api/authentication/strategies") if s["module"] == "oidc" and s["displayName"] == SSO_NAME]
    if existing:
        strategy = existing[0]["id"]
        # The secret is masked when read back, so the strategy is rewritten every time: same result.
        wiki.call("PUT", f"/_api/authentication/strategies/{strategy}", wanted)
        state = "updated"
    else:
        strategy = wiki.call("POST", "/_api/authentication/strategies", {"module": "oidc", **wanted})["id"]
        state = "created"
    offered = [{"id": LOCAL_STRATEGY, "order": 0, "isVisible": True}, {"id": strategy, "order": 1, "isVisible": True}]
    wiki.call("PUT", f"/_api/sites/{wiki.site}", {"authStrategies": offered})
    return f"sign-in: Authentik {state}, offered beside the local sign-in (callback {wiki.base}/_api/auth/{strategy}/callback)"


def pull(wiki):
    _, target = wiki.git_target()
    message = wiki.action(target, "sync")
    before = wiki.page_count()
    if "Import Everything" in message or before == 0:
        # First contact with the branch: the wiki takes the remote as it stands and waits to be told to import.
        message = wiki.action(target, "importAll")
    for _ in range(30):
        time.sleep(2)
        count = wiki.page_count()
        if count and count == before:
            break
        before = count
    return f"storage: {message.split('.')[0].strip()}; {wiki.page_count()} pages"


def status(wiki):
    storage, target = wiki.git_target()
    health = wiki.call("GET", f"/_api/sites/{wiki.site}/storage/status")
    state = next(t["state"]["status"] for t in health["targets"] if t["id"] == target["id"])
    strategies = [f"{s['displayName']} ({s['module']}, {'on' if s['isEnabled'] else 'off'})" for s in wiki.call("GET", "/_api/authentication/strategies")]
    config = target.get("config") or {}
    return (f"pages: {wiki.page_count()}\nGit storage: {'enabled' if target['isEnabled'] else 'disabled'}, {state}, "
            f"{config.get('syncMode')} {config.get('branch')} every {storage.get('syncInterval')}\nsign-in: {', '.join(strategies)}")


def main(argv):
    if len(argv) != 1 or argv[0] not in ("configure", "sync", "status"):
        print(__doc__, file=sys.stderr)
        return 2
    password = os.environ.get("WIKI_ADMIN_PASSWORD")
    secret = os.environ.get("SSO_WIKI_CLIENT_SECRET")
    if not password or (argv[0] == "configure" and not secret):
        print("wiki-admin: set WIKI_ADMIN_PASSWORD (store path /wiki) and, for configure, SSO_WIKI_CLIENT_SECRET (/authentik)", file=sys.stderr)
        return 2
    wiki = Wiki()
    try:
        wiki.sign_in(password)
        if argv[0] == "configure":
            for step in (configure_site, configure_storage, lambda w: configure_sso(w, secret), pull):
                print(step(wiki))
        elif argv[0] == "sync":
            print(pull(wiki))
        else:
            print(status(wiki))
    except Stop as stop:
        print(f"wiki-admin: {stop}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
