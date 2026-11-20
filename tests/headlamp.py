#!/usr/bin/env python3
"""Headlamp (M005): render the pinned official chart with our values and check the access rules.

Needs `helm` and the chart download; no cluster access.
"""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def main():
    version, repo = make_var("HEADLAMP_CHART_VERSION"), make_var("HEADLAMP_REPO")
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "the chart version is pinned"
    rendered = subprocess.run(
        ["helm", "template", "headlamp", "headlamp", "--repo", repo, "--version", version, "--namespace", "headlamp",
         "-f", str(ROOT / "services/headlamp/values.yaml")], capture_output=True, text=True)
    assert rendered.returncode == 0, rendered.stderr
    docs = [d for d in yaml.safe_load_all(rendered.stdout) if d]
    kinds = {d["kind"] for d in docs}
    assert "ClusterRoleBinding" not in kinds, "Headlamp's own ServiceAccount must hold no cluster rights"
    ingress = next(d for d in docs if d["kind"] == "Ingress")
    annotations = ingress["metadata"]["annotations"]
    assert annotations["traefik.ingress.kubernetes.io/router.entrypoints"] == "websecure"
    assert annotations["traefik.ingress.kubernetes.io/router.middlewares"] == "headlamp-admin-lan@kubernetescrd"
    assert [r["host"] for r in ingress["spec"]["rules"]] == ["headlamp.doku-lab.net"]
    deployment = next(d for d in docs if d["kind"] == "Deployment")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["limits"]["memory"] == "256Mi"
    assert container["securityContext"]["runAsNonRoot"] is True

    makefile = (ROOT / "Makefile").read_text()
    access = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((ROOT / "services/headlamp/access.yaml").read_text())}
    middleware = access[("Middleware", "admin-lan")]
    assert middleware["metadata"]["namespace"] == "headlamp"
    assert middleware["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"], "administration LAN only"
    binding = access[("ClusterRoleBinding", "headlamp-admin")]
    assert binding["subjects"] == [{"kind": "ServiceAccount", "name": "headlamp-admin", "namespace": "headlamp"}]
    assert access[("Secret", "headlamp-admin-token")]["type"] == "kubernetes.io/service-account-token"
    assert "data" not in access[("Secret", "headlamp-admin-token")], "no token value in Git"

    # Sign-in through Authentik (ADR-017): Headlamp reads its client from a Secret that is not in Git, and the
    # people's rights are a binding of the prefixed group, which only the API servers' setting can produce.
    assert container["envFrom"] == [{"secretRef": {"name": "headlamp-oidc"}}]
    args = container["args"]
    assert {"-oidc-client-id=$(OIDC_CLIENT_ID)", "-oidc-client-secret=$(OIDC_CLIENT_SECRET)",
            "-oidc-idp-issuer-url=$(OIDC_ISSUER_URL)", "-oidc-scopes=$(OIDC_SCOPES)"} <= set(args), args
    assert "-unsafe-use-service-account-token" not in args and "-oidc-auto-login=$(OIDC_AUTO_LOGIN)" not in args, "the token login stays offered"
    assert not [d for d in docs if d["kind"] == "Secret"], "the chart writes no Secret: the client secret is not in Git"
    people = access[("ClusterRoleBinding", "oidc-homelab-admins")]
    assert people["roleRef"]["name"] == "cluster-admin"
    assert people["subjects"] == [{"apiGroup": "rbac.authorization.k8s.io", "kind": "Group", "name": "oidc:homelab-admins"}]
    defaults = yaml.safe_load((ROOT / "ansible/roles/k3s/defaults/main.yml").read_text())
    assert defaults["k3s_oidc_prefix"] == "oidc:" and defaults["k3s_oidc_client_id"] == "headlamp"
    assert defaults["k3s_oidc_issuer"] == make_var("HEADLAMP_OIDC_ISSUER"), "Headlamp and the API servers name the same issuer"
    assert make_var("HEADLAMP_OIDC_SCOPES").split(",") == ["openid", "profile", "email", "offline_access"]
    recipe = re.search(r"^headlamp-deploy:.*?(?=^\S)", makefile + "\nend:\n", re.M | re.S).group(0)
    assert "headlamp-oidc" in recipe and "SSO_HEADLAMP_CLIENT_SECRET" in recipe and "--from-env-file=<(" in recipe

    # The allow-list only works when Traefik sees the real client address.
    traefik = (ROOT / "ansible/roles/k3s/templates/traefik-config.yaml.j2").read_text()
    assert "externalTrafficPolicy: Local" in traefik
    assert "HEADLAMP_DEPLOY_APPROVED" in makefile and "jsonpath='{.data.token}'" in makefile
    print("PASS: Headlamp chart pinned, no cluster rights for the app, HTTPS + admin-LAN ingress, token never in Git")


if __name__ == "__main__":
    main()
