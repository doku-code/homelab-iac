#!/usr/bin/env python3
"""Signs in to every application through Authentik, as a browser would, and reports what each application
then says about the person (M014, ADR-017).

  scripts/sso-check.py [application ...]      default: all of argocd grafana netbox windmill

It uses Authentik's first administrator (akadmin) with the password of the secret store, so it works as long as
that account keeps this password and has no second factor; give the account a second factor and this check
stops at "needs a second factor", which is then the expected result. Credentials come from the environment only
(AUTHENTIK_BOOTSTRAP_PASSWORD, store path /authentik) and are never printed. Nothing is changed anywhere, apart
from what a first sign-in does by itself: the application creates its record of the person.
"""
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AUTHENTIK = os.environ.get("AUTHENTIK_URL", "https://auth.doku-lab.net")
USER = "akadmin"
GROUP = "homelab-admins"


class Stop(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    """Cookies and redirects handled by hand, so every hop can be inspected."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method, url, body=None, headers=None, form=None):
        data = None if body is None else json.dumps(body).encode()
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
        request = urllib.request.Request(url, data=data, method=method, headers={"Accept": "application/json", **(headers or {})})
        if data is not None:
            request.add_header("Content-Type", "application/x-www-form-urlencoded" if form is not None else "application/json")
        try:
            with self.opener.open(request, timeout=60) as response:
                return response.status, dict(response.headers), response.read().decode(errors="replace")
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read().decode(errors="replace")

    def cookie(self, name):
        return next((c.value for c in self.jar if c.name == name), None)

    def follow(self, url, until, limit=12):
        """GET and follow redirects until `until(url)` is true for the next address; returns that address."""
        for _ in range(limit):
            if until(url):
                return url
            status, headers, _ = self.request("GET", url)
            if status not in (301, 302, 303, 307, 308) or "Location" not in headers:
                raise Stop(f"expected a redirect from {url.split('?')[0]}, got HTTP {status}")
            url = urllib.parse.urljoin(url, headers["Location"])
        raise Stop("too many redirects")

    def flow(self, url, password):
        """Runs one Authentik flow (the page at /if/flow/<slug>/?<query>) through its API; returns where it sends the browser."""
        parsed = urllib.parse.urlparse(url)
        slug = parsed.path.rstrip("/").split("/")[-1]
        executor = f"{AUTHENTIK}/api/v3/flows/executor/{slug}/?query={urllib.parse.quote(parsed.query)}"
        status, _, text = self.request("GET", executor)
        for _ in range(8):
            if status != 200:
                raise Stop(f"flow {slug}: HTTP {status}")
            challenge = json.loads(text)
            component = challenge.get("component")
            if component == "xak-flow-redirect":
                return urllib.parse.urljoin(AUTHENTIK, challenge["to"])
            if component == "ak-stage-identification":
                answer = {"component": component, "uid_field": USER}
                if challenge.get("password_fields"):
                    answer["password"] = password
            elif component == "ak-stage-password":
                answer = {"component": component, "password": password}
            elif component == "ak-stage-authenticator-validate":
                raise Stop("needs a second factor (expected once the account has one)")
            elif component == "ak-stage-access-denied":
                raise Stop(f"Authentik denies access: {challenge.get('error_message') or 'no reason given'}")
            else:
                raise Stop(f"flow {slug}: unexpected step {component}")
            csrf = self.cookie("authentik_csrf")
            status, _, text = self.request("POST", executor, answer, {"X-authentik-CSRF": csrf} if csrf else None)
            if status == 200 and json.loads(text).get("response_errors"):
                raise Stop(f"flow {slug}: {component} refused the answer")
            for _ in range(6):  # accepted answers and steps without a question answer with a redirect to the same address
                if status != 302:
                    break
                status, _, text = self.request("GET", executor)
        raise Stop(f"flow {slug}: did not finish")

    def sign_in(self, start, password, callback_prefix, first_hop=None):
        """From the application's sign-in address to its callback address (with the authorization code).
        `first_hop` is the address the application already answered with when its sign-in is a form."""
        is_flow = lambda u: u.startswith(f"{AUTHENTIK}/if/flow/")  # noqa: E731
        is_callback = lambda u: u.startswith(callback_prefix)  # noqa: E731
        url = self.follow(first_hop or start, lambda u: is_flow(u) or is_callback(u))
        for _ in range(4):
            if is_callback(url):
                return url
            url = self.follow(self.flow(url, password), lambda u: is_flow(u) or is_callback(u))
        raise Stop("no callback after four flows")


def argocd(browser, password):
    base = "https://argocd.doku-lab.net"
    callback = browser.sign_in(f"{base}/auth/login?return_url={urllib.parse.quote(base + '/applications')}", password, f"{base}/auth/callback")
    browser.follow(callback, lambda u: not u.startswith(f"{base}/auth/"))
    _, _, text = browser.request("GET", f"{base}/api/v1/session/userinfo")
    info = json.loads(text)
    status, _, apps = browser.request("GET", f"{base}/api/v1/applications?fields=items.metadata.name")
    count = len(json.loads(apps).get("items") or []) if status == 200 else 0
    ok = info.get("loggedIn") is True and GROUP in (info.get("groups") or []) and count > 0
    return ok, f"signed in as {info.get('username')}, groups {info.get('groups')}, sees {count} applications"


def grafana(browser, password):
    base = "https://grafana.doku-lab.net"
    callback = browser.sign_in(f"{base}/login/generic_oauth", password, f"{base}/login/generic_oauth?")
    browser.follow(callback, lambda u: "/login/generic_oauth" not in u)
    status, _, text = browser.request("GET", f"{base}/api/user")
    user = json.loads(text) if status == 200 else {}
    _, _, org = browser.request("GET", f"{base}/api/user/orgs")
    roles = [o.get("role") for o in json.loads(org)] if status == 200 else []
    ok = user.get("login") == USER and user.get("isGrafanaAdmin") is True and roles == ["Admin"]
    return ok, f"signed in as {user.get('login')}, server administrator: {user.get('isGrafanaAdmin')}, organisation roles {roles}"


def netbox(browser, password):
    base = "https://netbox.doku-lab.net"
    # NetBox's button is a form: the login page gives the token the form must carry.
    browser.request("GET", f"{base}/login/", headers={"Accept": "text/html"})
    status, headers, _ = browser.request("POST", f"{base}/oauth/login/oidc/", headers={"Referer": f"{base}/login/"},
                                         form={"csrfmiddlewaretoken": browser.cookie("csrftoken") or "", "next": "/"})
    if status != 302:
        raise Stop(f"NetBox did not start the sign-in: HTTP {status}")
    callback = browser.sign_in(None, password, f"{base}/oauth/complete/oidc/", first_hop=urllib.parse.urljoin(base, headers["Location"]))
    browser.follow(callback, lambda u: "/oauth/" not in u)
    # NetBox's API does not show the superuser flag. An account without any NetBox permission can only list
    # accounts and other people's API tokens when it is a superuser, so that is what is tested.
    status, _, text = browser.request("GET", f"{base}/api/users/users/?username={USER}")
    users = json.loads(text).get("results", []) if status == 200 else []
    tokens, _, _ = browser.request("GET", f"{base}/api/users/tokens/")
    unprivileged = len(users) == 1 and not users[0].get("permissions") and not users[0].get("groups")
    ok = status == 200 and tokens == 200 and unprivileged and users[0].get("is_active") is True
    return ok, f"signed in as {USER}, reads accounts (HTTP {status}) and API tokens (HTTP {tokens}) without any assigned permission: superuser"


def windmill(browser, password):
    base = "https://windmill.doku-lab.net"
    callback = browser.sign_in(f"{base}/api/oauth/login/authentik", password, f"{base}/user/login_callback/authentik")
    # The callback address is a page of Windmill's interface; the page hands code and state to the API.
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(callback).query))
    status, _, text = browser.request("POST", f"{base}/api/oauth/login_callback/authentik", {"code": query.get("code"), "state": query.get("state")})
    if status != 200:
        raise Stop(f"Windmill refused the sign-in: HTTP {status} {text[:200]}")
    _, _, text = browser.request("GET", f"{base}/api/users/whoami")
    me = json.loads(text)
    _, _, text = browser.request("GET", f"{base}/api/workspaces/users")
    workspaces = [w.get("id") for w in json.loads(text).get("workspaces", [])]
    ok = me.get("super_admin") is True and me.get("login_type") == "authentik" and "homelab" in workspaces
    return ok, f"signed in as {me.get('email')}, administrator: {me.get('super_admin')}, workspaces {workspaces}"


def homepage(browser, password):
    """Forward authentication: Traefik sends an unknown visitor to Authentik and lets the session through afterwards."""
    base = "https://home.doku-lab.net"
    outpost = f"{base}/outpost.goauthentik.io/"
    anonymous, _, _ = browser.request("GET", f"{base}/api/snapshot")
    if anonymous == 200:
        return False, "the widget API answers without a session"
    callback = browser.sign_in(f"{base}/", password, f"{outpost}callback")
    browser.follow(callback, lambda u: not u.startswith(outpost))
    page, _, text = browser.request("GET", f"{base}/")
    status, _, snapshot = browser.request("GET", f"{base}/api/snapshot")
    nodes = json.loads(snapshot).get("nodes", {}) if status == 200 else {}
    ok = page == 200 and "__NEXT_DATA__" in text and status == 200 and bool(nodes)
    return ok, f"HTTP {anonymous} without a session; signed in: page HTTP {page}, widget data for {len(nodes)} nodes"


def proxmox(browser, password):
    """Proxmox asks Authentik through its API: an address to send the browser to, then the code it came back with."""
    base, realm = "https://pve-management.doku-lab.net", "authentik"
    status, _, text = browser.request("POST", f"{base}/api2/json/access/openid/auth-url", form={"realm": realm, "redirect-url": base})
    if status != 200:
        raise Stop(f"Proxmox did not start the sign-in: HTTP {status}")
    callback = browser.sign_in(None, password, f"{base}?", first_hop=json.loads(text)["data"])
    query = urllib.parse.parse_qs(urllib.parse.urlparse(callback).query)
    status, _, text = browser.request("POST", f"{base}/api2/json/access/openid/login",
                                      form={"code": query["code"][0], "state": query["state"][0], "redirect-url": base})
    if status != 200:
        raise Stop(f"Proxmox refused the sign-in: HTTP {status}")
    session = json.loads(text)["data"]
    cookie = {"Cookie": "PVEAuthCookie=" + urllib.parse.quote(session["ticket"], safe="")}
    status, _, text = browser.request("GET", f"{base}/api2/json/access/permissions?path=/", headers=cookie)
    rights = json.loads(text)["data"].get("/", {}) if status == 200 else {}
    _, _, text = browser.request("GET", f"{base}/api2/json/access/users/{urllib.parse.quote(session['username'])}", headers=cookie)
    groups = json.loads(text).get("data", {}).get("groups", [])
    ok = session["username"] == f"{USER}@{realm}" and f"{GROUP}-{realm}" in groups and rights.get("Sys.Modify") == 1 and rights.get("VM.Allocate") == 1
    return ok, f"signed in as {session['username']}, groups {groups}, {len(rights)} privileges on /"


CHECKS = {"argocd": argocd, "grafana": grafana, "netbox": netbox, "windmill": windmill, "homepage": homepage, "proxmox": proxmox}


def main(argv):
    password = os.environ.get("AUTHENTIK_BOOTSTRAP_PASSWORD")
    if not password:
        print("sso-check: set AUTHENTIK_BOOTSTRAP_PASSWORD in the environment (store path /authentik)", file=sys.stderr)
        sys.exit(2)
    unknown = [name for name in argv if name not in CHECKS]
    if unknown:
        print(f"sso-check: unknown application {unknown[0]}; known: {' '.join(CHECKS)}", file=sys.stderr)
        sys.exit(2)
    failed = 0
    for name in argv or list(CHECKS):
        try:
            ok, detail = CHECKS[name](Browser(), password)
        except Stop as stop:
            ok, detail = False, str(stop)
        except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError, KeyError) as error:
            ok, detail = False, f"{type(error).__name__}: {error}"
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name:<9} {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
