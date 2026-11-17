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
    assert [r["host"] for r in ingress["spec"]["rules"]] == ["headlamp.192.168.0.40.sslip.io"]
    deployment = next(d for d in docs if d["kind"] == "Deployment")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["limits"]["memory"] == "256Mi"
    assert container["securityContext"]["runAsNonRoot"] is True

    access = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((ROOT / "services/headlamp/access.yaml").read_text())}
    middleware = access[("Middleware", "admin-lan")]
    assert middleware["metadata"]["namespace"] == "headlamp"
    assert middleware["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"], "administration LAN only"
    binding = access[("ClusterRoleBinding", "headlamp-admin")]
    assert binding["subjects"] == [{"kind": "ServiceAccount", "name": "headlamp-admin", "namespace": "headlamp"}]
    assert access[("Secret", "headlamp-admin-token")]["type"] == "kubernetes.io/service-account-token"
    assert "data" not in access[("Secret", "headlamp-admin-token")], "no token value in Git"

    # The allow-list only works when Traefik sees the real client address.
    traefik = (ROOT / "ansible/roles/k3s/templates/traefik-config.yaml.j2").read_text()
    assert "externalTrafficPolicy: Local" in traefik
    makefile = (ROOT / "Makefile").read_text()
    assert "HEADLAMP_DEPLOY_APPROVED" in makefile and "jsonpath='{.data.token}'" in makefile
    print("PASS: Headlamp chart pinned, no cluster rights for the app, HTTPS + admin-LAN ingress, token never in Git")


if __name__ == "__main__":
    main()
