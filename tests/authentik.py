#!/usr/bin/env python3
"""Authentik (M014, ADR-017): render the pinned official chart with our values, check the route, the database
entry, the blueprints and that every application signing in through Authentik is wired on both sides.

Needs `helm` and the chart download; no cluster or Authentik access.
"""
import importlib.util
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/authentik"
HOST = "auth.doku-lab.net"
ISSUER = f"https://{HOST}/application/o"
DEFAULTS = {"Default - Provider authorization flow (implicit consent)", "Default - Provider invalidation flow",
            "System - OAuth2 Provider - Scopes"}


class Tag:
    """A blueprint tag (!Env, !Find, !KeyOf): kept as name and value so the test can inspect it."""

    def __init__(self, name, value):
        self.name, self.value = name, value

    def __eq__(self, other):
        return isinstance(other, Tag) and (self.name, self.value) == (other.name, other.value)

    def __repr__(self):
        return f"!{self.name} {self.value}"


class BlueprintLoader(yaml.SafeLoader):
    pass


def _tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return Tag(suffix, loader.construct_scalar(node))
    return Tag(suffix, loader.construct_sequence(node, deep=True))


BlueprintLoader.add_multi_constructor("!", _tag)


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def recipe(target):
    return re.search(rf"^{target}:.*?(?=^\S)", (ROOT / "Makefile").read_text() + "\nend:\n", re.M | re.S).group(0)


def chart():
    result = subprocess.run(["helm", "template", "authentik", "authentik", "--repo", make_var("AUTHENTIK_REPO"), "--version",
                             make_var("AUTHENTIK_CHART_VERSION"), "--namespace", "authentik", "-f", str(DIR / "values.yaml")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    kinds = {d["kind"] for d in docs}
    assert kinds == {"Deployment", "Service"}, f"no Secret, no bundled database, no rights in the cluster, no chart ingress: {kinds}"
    deployments = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Deployment"}
    assert set(deployments) == {"authentik-server", "authentik-worker"}
    for name, deployment in deployments.items():
        assert deployment["spec"]["replicas"] == 1, f"{name}: one replica per service for now"
        pod = deployment["spec"]["template"]["spec"]
        assert pod["automountServiceAccountToken"] is False, f"{name}: Authentik gets no Kubernetes credentials"
        (container,) = pod["containers"]
        assert re.fullmatch(r"ghcr\.io/goauthentik/server:\d+\.\d+\.\d+", container["image"]), container["image"]
        assert container["resources"]["requests"]["memory"] and container["resources"]["limits"]["memory"]
        assert container["envFrom"] == [{"secretRef": {"name": "authentik-secrets"}}], "every secret comes from one Secret outside Git"
        env = {e["name"]: e.get("value") for e in container["env"]}
        assert env["AUTHENTIK_POSTGRESQL__HOST"] == "192.168.0.60" and env["AUTHENTIK_POSTGRESQL__SSLMODE"] == "require"
        assert env["AUTHENTIK_DISABLE_UPDATE_CHECK"] == "true" and env["AUTHENTIK_AVATARS"] == "initials", "nothing calls out of the LAN"
        assert not [n for n in env if re.search(r"PASSWORD|SECRET|TOKEN", n)], "no secret among the plain values"
    worker = deployments["authentik-worker"]["spec"]["template"]["spec"]
    assert {"name": "blueprints-cm-authentik-blueprints", "configMap": {"name": "authentik-blueprints"}} in worker["volumes"]


def access_database_and_make():
    docs = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d]
    (route,) = [d for d in docs if d["kind"] == "IngressRoute"]
    rule, _outpost = route["spec"]["routes"]  # the second route is checked by forward_auth()
    assert rule["match"] == f"Host(`{HOST}`)" and rule["middlewares"] == [{"name": "admin-lan"}] and route["spec"]["tls"] == {}
    assert rule["services"] == [{"name": "authentik-server", "port": 80}]
    (allow,) = [d for d in docs if d["kind"] == "Middleware"]
    assert allow["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24", "10.42.0.0/16"], "the LAN, and the pods that exchange tokens"
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == "192.168.0.40"
    apps = {a["name"] for a in yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]}
    assert "authentik" in apps
    deploy = recipe("authentik-deploy")
    assert 'test "$(AUTHENTIK_DEPLOY_APPROVED)" = yes' in deploy and "helm " not in deploy, "Argo CD installs the chart"
    assert "AUTHENTIK_POSTGRESQL__PASSWORD=%s" in deploy and "--from-env-file=<(" in deploy, "values go from the environment into the Secret"
    assert 'test "$(AUTHENTIK_SECRETS_APPROVED)" = yes' in recipe("authentik-secrets")


def blueprints():
    """Every file is in the ConfigMap; every application has a confidential client whose secret comes from the
    environment, exact https redirect addresses on our domain, and is open to named groups only."""
    kustomization = yaml.safe_load((DIR / "kustomization.yaml").read_text())
    (generator,) = kustomization["configMapGenerator"]
    files = sorted(DIR.glob("blueprints/*.yaml"))
    assert sorted(generator["files"]) == [str(f.relative_to(DIR)) for f in files], "kustomization.yaml lists every blueprint"
    assert generator["name"] == "authentik-blueprints" and kustomization["generatorOptions"]["disableNameSuffixHash"] is True
    clients, forward = set(make_var("AUTHENTIK_CLIENTS").split()), set(make_var("AUTHENTIK_FORWARD_AUTH").split())
    declared, protected, names = set(), set(), set()
    for file in files:
        text = file.read_text()
        assert not re.search(r"client_secret: (?!!Env SSO_[A-Z]+_CLIENT_SECRET$).*$", text, re.M), f"{file.name}: a client secret in Git"
        blueprint = yaml.load(text, Loader=BlueprintLoader)
        assert blueprint["version"] == 1 and blueprint["metadata"]["name"].startswith("Homelab - "), file.name
        assert blueprint["metadata"]["name"] not in names, "blueprint names are unique"
        names.add(blueprint["metadata"]["name"])
        entries = blueprint["entries"]
        assert not [e for e in entries if e.get("state") == "absent"], f"{file.name}: blueprints never delete"
        providers = [e for e in entries if e["model"] in ("authentik_providers_oauth2.oauth2provider", "authentik_providers_proxy.proxyprovider")]
        applications = [e for e in entries if e["model"] == "authentik_core.application"]
        if not applications:
            continue
        required = {e["attrs"]["identifiers"]["name"] for e in entries if e["model"] == "authentik_blueprints.metaapplyblueprint" and e["attrs"]["required"]}
        assert DEFAULTS <= required, f"{file.name}: must wait for Authentik's defaults"
        (provider,), (application,) = providers, applications
        slug = application["identifiers"]["slug"]
        assert file.name == f"homelab-{slug}.yaml" and provider["identifiers"] == {"name": slug}
        attrs = provider["attrs"]
        assert application["attrs"]["provider"] == Tag("KeyOf", provider["id"])
        bindings = [e for e in entries if e["model"] == "authentik_policies.policybinding"]
        assert bindings and all(b["identifiers"]["target"] == Tag("KeyOf", application["id"]) and b["identifiers"]["group"].name == "KeyOf"
                                for b in bindings), f"{slug}: open to named groups only"
        if provider["model"] == "authentik_providers_proxy.proxyprovider":
            # Forward authentication: one name of our domain, checked by Traefik; no secret shared with the application.
            assert attrs["mode"] == "forward_single" and re.fullmatch(r"https://[a-z0-9-]+\.doku-lab\.net", attrs["external_host"]), slug
            assert "client_secret" not in attrs and "internal_host" not in attrs
            protected.add(slug.upper())
            continue
        assert attrs["client_type"] == "confidential" and attrs["client_id"] == slug
        assert attrs["client_secret"] == Tag("Env", f"SSO_{slug.upper()}_CLIENT_SECRET")
        assert attrs["signing_key"].name == "Find", "tokens are signed with a key pair, which every client can verify"
        assert attrs["grant_types"] == ["authorization_code", "refresh_token"], "no grant is allowed unless listed (2026.5+)"
        assert attrs["redirect_uris"], slug
        # Proxmox sends the browser's own address without a path: its four names and its four node addresses.
        allowed = {"proxmox": r"https://(pve-(management|core|infra|lab)\.doku-lab\.net|192\.168\.0\.1[0126]:8006)"}.get(
            slug, rf"https://{slug}\.doku-lab\.net/[\w/.-]*")
        # The wiki generates the identifier in its callback address: one anchored pattern, this host and path only.
        patterns = {"wiki": r"^https://wiki\.doku-lab\.net/_api/auth/[0-9a-f-]{36}/callback$"}
        for redirect in attrs["redirect_uris"]:
            if redirect["matching_mode"] == "regex":
                assert redirect["url"] == patterns.get(slug), redirect
                continue
            assert redirect["matching_mode"] == "strict" and re.fullmatch(allowed, redirect["url"]), redirect
        declared.add(slug.upper())
    assert declared == clients, f"AUTHENTIK_CLIENTS in the Makefile and the blueprints disagree: {declared ^ clients}"
    assert protected == forward, f"AUTHENTIK_FORWARD_AUTH in the Makefile and the blueprints disagree: {protected ^ forward}"
    # The embedded outpost serves exactly the forward-authentication providers, after their blueprints.
    outpost = yaml.load((DIR / "blueprints/homelab-outpost.yaml").read_text(), Loader=BlueprintLoader)
    (entry,) = [e for e in outpost["entries"] if e["model"] == "authentik_outposts.outpost"]
    assert entry["identifiers"] == {"managed": "goauthentik.io/outposts/embedded"} and set(entry["attrs"]) == {"providers"}, "no Kubernetes connection, no other setting"
    served = {p.value[1][1].upper() for p in entry["attrs"]["providers"]}
    assert all(p.name == "Find" and p.value[0] == "authentik_providers_proxy.proxyprovider" for p in entry["attrs"]["providers"]) and served == forward
    waits = {e["attrs"]["identifiers"]["name"] for e in outpost["entries"] if e["model"] == "authentik_blueprints.metaapplyblueprint" and e["attrs"]["required"]}
    assert waits == {n for n in names if n.split(" - ")[1].upper() in forward}, "the outpost waits for the blueprint of each provider it serves"
    access = yaml.load((DIR / "blueprints/homelab-access.yaml").read_text(), Loader=BlueprintLoader)
    groups = [e for e in access["entries"] if e["model"] == "authentik_core.group"]
    assert [g["identifiers"]["name"] for g in groups] == ["homelab-admins"] and groups[0]["attrs"]["is_superuser"] is False
    users = [e for e in access["entries"] if e["model"] == "authentik_core.user"]
    assert [u["identifiers"] for u in users] == [{"username": "akadmin"}], "people are managed in Authentik, not in Git"
    assert "password" not in str(users[0]["attrs"])


def clients():
    """Each application of AUTHENTIK_CLIENTS is configured on its own side with the same client name and the
    addresses of its own provider, reads its client secret from a Secret or the environment, and keeps a local
    administrator. A new client must be added here: that is the reminder to wire both sides."""
    make = (ROOT / "Makefile").read_text()

    argocd = yaml.safe_load((ROOT / "services/argocd/values.yaml").read_text())["configs"]
    oidc = yaml.safe_load(argocd["cm"]["oidc.config"])
    assert oidc["issuer"] == f"{ISSUER}/argocd/" and oidc["clientID"] == "argocd" and oidc["clientSecret"] == "$argocd-sso:clientSecret"
    assert "groups" not in oidc["requestedScopes"], "Authentik sends the groups with the profile scope"
    assert argocd["rbac"]["policy.default"] == "" and argocd["rbac"]["policy.csv"].strip() == "g, homelab-admins, role:admin"
    assert "admin.enabled" not in argocd["cm"], "the local administrator stays"
    deploy = recipe("argocd-deploy")
    assert "argocd-sso" in deploy and "app.kubernetes.io/part-of=argocd" in deploy and "SSO_ARGOCD_CLIENT_SECRET" in deploy

    grafana = yaml.safe_load((ROOT / "services/observability/grafana.yaml").read_text())
    oauth = grafana["grafana.ini"]["auth.generic_oauth"]
    assert oauth["enabled"] is True and oauth["client_id"] == "grafana" and "client_secret" not in oauth
    assert (oauth["auth_url"], oauth["token_url"], oauth["api_url"]) == (f"{ISSUER}/authorize/", f"{ISSUER}/token/", f"{ISSUER}/userinfo/")
    assert oauth["role_attribute_path"] == "contains(groups[*], 'homelab-admins') && 'GrafanaAdmin'" and oauth["role_attribute_strict"] is True
    assert "oauth_auto_login" not in oauth and "disable_login_form" not in grafana["grafana.ini"].get("auth", {}), "the login form stays"
    reference = grafana["envValueFrom"]["GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET"]["secretKeyRef"]
    assert reference == {"name": "grafana-sso", "key": "clientSecret", "optional": True}, "Grafana starts without single sign-on"
    assert "grafana-sso" in recipe("observability-deploy")

    netbox = yaml.safe_load((ROOT / "services/netbox/values.yaml").read_text())
    assert netbox["remoteAuth"] == {"enabled": True, "backends": ["social_core.backends.open_id_connect.OpenIdConnectAuth"]}
    settings = netbox["extraConfig"][0]["values"]
    assert settings["SOCIAL_AUTH_OIDC_OIDC_ENDPOINT"] == f"{ISSUER}/netbox/" and settings["SOCIAL_AUTH_OIDC_KEY"] == "netbox"
    assert "SOCIAL_AUTH_OIDC_SECRET" not in str(netbox) and settings["SOCIAL_AUTH_PIPELINE"][-1] == "netbox.sso_pipeline.set_superuser"
    assert netbox["extraConfig"][1] == {"secret": {"secretName": "netbox-sso", "optional": True}}, "NetBox starts without single sign-on"
    assert "netbox-sso" in recipe("netbox-deploy") and "SOCIAL_AUTH_OIDC_SECRET" in recipe("netbox-deploy")

    spec = importlib.util.spec_from_file_location("windmill_admin", ROOT / "scripts/windmill-admin.py")
    windmill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(windmill)
    client = windmill.sso_client("synthetic")
    assert client["id"] == "windmill" and client["secret"] == "synthetic" and client["pkce"] is True
    assert client["login_config"]["token_url"] == f"{ISSUER}/token/" and "email" in client["login_config"]["scopes"]
    assert 'test "$(WINDMILL_SSO_APPROVED)" = yes' in recipe("windmill-sso")

    # Proxmox: one realm for the cluster, written over SSH; the secret travels on standard input, people and
    # groups come from Authentik, only homelab-admins gets rights, and nothing existing is changed.
    proxmox = recipe("proxmox-sso")
    settings = make_var("PROXMOX_SSO_SETTINGS")
    assert 'test "$(PROXMOX_SSO_APPROVED)" = yes' in proxmox and make_var("PROXMOX_SSO_ISSUER") == f"{ISSUER}/proxmox/"
    assert "--client-id proxmox" in settings and "--groups-claim groups" in settings and "--autocreate 1" in settings
    assert "--default" not in settings + proxmox, "the sign-in page keeps its default realm"
    assert "SSO_PROXMOX_CLIENT_SECRET" in proxmox and "IFS= read -r key" in proxmox and "--username-claim preferred_username" in proxmox
    assert proxmox.count("acl modify") == 1 and "--groups $(PROXMOX_SSO_GROUP) --roles Administrator" in proxmox
    assert make_var("PROXMOX_SSO_GROUP") == "homelab-admins-$(PROXMOX_SSO_REALM)"
    assert not re.search(r"pveum (user|realm) (delete|del)|passwd|root@pam", proxmox), "root@pam and the other accounts are untouched"

    # The wiki: configured through its API by scripts/wiki-admin.py, secret from the environment, local sign-in kept.
    spec = importlib.util.spec_from_file_location("wiki_admin", ROOT / "scripts/wiki-admin.py")
    wiki = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wiki)
    config = wiki.sso_config("synthetic")
    assert config["clientId"] == "wiki" and config["clientSecret"] == "synthetic" and config["issuer"] == f"{ISSUER}/wiki/"
    assert config["useDiscovery"] is True and "email" in config["scopes"]
    assert 'test "$(WIKI_CONFIGURE_APPROVED)" = yes' in recipe("wiki-configure")

    checked = {"ARGOCD", "GRAFANA", "NETBOX", "PROXMOX", "WIKI", "WINDMILL"}
    assert set(make_var("AUTHENTIK_CLIENTS").split()) == checked, "add the new client's own side to this test"


def forward_auth():
    """An application of AUTHENTIK_FORWARD_AUTH puts Authentik's check on every route of its name, and the sign-in
    paths of every name of the domain reach the embedded outpost, from the LAN only."""
    documents = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d]
    (route,) = [d for d in documents if d["kind"] == "IngressRoute"]
    (outpost,) = [r for r in route["spec"]["routes"] if "outpost.goauthentik.io" in r["match"]]
    assert outpost["match"] == "HostRegexp(`^[a-z0-9-]+\\.doku-lab\\.net$`) && PathPrefix(`/outpost.goauthentik.io/`)"
    assert outpost["middlewares"] == [{"name": "admin-lan"}] and outpost["services"] == [{"name": "authentik-server", "port": 80}]
    assert outpost["priority"] >= 1000, "wins over the application's own routes"
    for name in make_var("AUTHENTIK_FORWARD_AUTH").split():
        service = ROOT / "services" / name.lower()
        objects = [d for d in yaml.safe_load_all((service / "access.yaml").read_text()) if d]
        (check,) = [d for d in objects if d["kind"] == "Middleware" and "forwardAuth" in d["spec"]]
        assert check["spec"]["forwardAuth"]["address"] == "http://authentik-server.authentik.svc.cluster.local/outpost.goauthentik.io/auth/traefik"
        blueprint = yaml.load((DIR / f"blueprints/homelab-{name.lower()}.yaml").read_text(), Loader=BlueprintLoader)
        (provider,) = [e for e in blueprint["entries"] if e["model"] == "authentik_providers_proxy.proxyprovider"]
        host = provider["attrs"]["external_host"].removeprefix("https://")
        routes = [r for d in objects if d["kind"] == "IngressRoute" for r in d["spec"]["routes"] if f"Host(`{host}`)" in r["match"]]
        assert routes and all({"name": check["metadata"]["name"]} in r["middlewares"] and {"name": "admin-lan"} in r["middlewares"]
                              for r in routes), f"{name}: every route of {host} asks Authentik"


def tools():
    """ensure-secrets never replaces a value and gives up when the store cannot be read; the admin tool only reads
    and re-applies blueprints."""
    spec = importlib.util.spec_from_file_location("ensure_secrets", ROOT / "scripts/ensure-secrets.py")
    ensure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ensure)
    calls, stored = [], []

    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if "run" in argv:
            return fake_run.read
        stored.append(kwargs["input"])
        return Result(0)

    ensure.subprocess.run = fake_run
    fake_run.read = Result(0, "KEPT\n")
    ensure.main(["/demo", "KEPT", "NEW_ONE"])
    (written,) = stored
    assert re.fullmatch(r"NEW_ONE=[0-9a-f]{64}\n", written), "only the missing key is written"
    fake_run.read = Result(2, "", "secrets: phase: no secrets at /demo")
    ensure.main(["/demo", "FIRST"])
    assert stored[-1].startswith("FIRST=") and len(stored) == 2
    fake_run.read = Result(2, "", "secrets: phase failed (exit 1); its output is withheld")
    try:
        ensure.main(["/demo", "KEPT"])
        raise AssertionError("an unreadable store must stop the generation")
    except SystemExit as stop:
        assert stop.code == 2 and len(stored) == 2, "nothing written when existing values cannot be seen"
    # The end-to-end check covers every client, prints no credential and writes nothing but its own sign-in.
    spec = importlib.util.spec_from_file_location("sso_check", ROOT / "scripts/sso-check.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    assert {name.upper() for name in check.CHECKS} == set((make_var("AUTHENTIK_CLIENTS") + " " + make_var("AUTHENTIK_FORWARD_AUTH")).split()), "one sign-in check per application"
    text = (ROOT / "scripts/sso-check.py").read_text()
    assert "print(password" not in text and '"DELETE"' not in text and '"PUT"' not in text and '"PATCH"' not in text
    browser = check.Browser()
    try:
        browser.follow("https://auth.doku-lab.net/x", lambda u: False, limit=0)
        raise AssertionError("a redirect chain must end")
    except check.Stop:
        pass
    text = (ROOT / "scripts/authentik-admin.py").read_text()
    assert '"DELETE"' not in text and "print(token" not in text
    assert set(re.findall(r'call\("(\w+)"', text)) == {"GET", "POST"} and set(re.findall(r'call\("POST", f?"([^"]+)"', text)) == {"/managed/blueprints/{blueprint['pk']}/apply/"} and text.count('call("POST"') == 2, "the only write is re-applying a blueprint"


def main():
    chart()
    access_database_and_make()
    blueprints()
    clients()
    forward_auth()
    tools()
    print("PASS: Authentik chart pinned with single replicas, no Kubernetes credentials, shared PostgreSQL over TLS, LAN and pod "
          "network route, blueprints with client secrets from the environment and group-restricted applications, six "
          "applications wired on both sides with their local administrator kept, forward authentication on every route of "
          "the applications without a login")


if __name__ == "__main__":
    main()
