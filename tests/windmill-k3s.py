#!/usr/bin/env python3
"""Windmill on k3s (M009): render the pinned official chart with our values, check the route, the database
roles and the scripts of windmill/.

Needs `helm` and the chart download; no cluster or Windmill access. (tests/windmill.py covers the retired
Compose deployment.)
"""
import ast
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/windmill"
HOST = "windmill.doku-lab.net"


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def chart():
    result = subprocess.run(["helm", "template", "windmill", "windmill", "--repo", make_var("WINDMILL_K3S_REPO"), "--version",
                             make_var("WINDMILL_K3S_CHART_VERSION"), "--namespace", "windmill", "-f", str(DIR / "values.yaml")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    kinds = [d["kind"] for d in docs]
    assert "Secret" not in kinds and "StatefulSet" not in kinds and "Ingress" not in kinds, "no bundled database, no secret, no chart ingress"
    deployments = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Deployment"}
    assert set(deployments) == {"windmill-app", "windmill-workers-default", "windmill-workers-native"}
    for name, deployment in deployments.items():
        assert deployment["spec"]["replicas"] == 1, f"{name}: one replica per service for now"
        (container,) = deployment["spec"]["template"]["spec"]["containers"]
        assert re.fullmatch(r"ghcr\.io/windmill-labs/windmill:\d+\.\d+\.\d+", container["image"]), container["image"]
        assert container["imagePullPolicy"] == "IfNotPresent" and container["resources"]["requests"]["memory"]
        assert not (container.get("securityContext") or {}).get("privileged"), f"{name}: no privileged container"
        env = {e["name"]: e for e in container["env"]}
        assert env["DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {"name": "windmill-secrets", "key": "url"}
        assert env["BASE_URL"]["value"] == f"https://{HOST}"
    make = (ROOT / "Makefile").read_text()
    recipe = re.search(r"^windmill-deploy:.*?(?=^\S)", make, re.M | re.S).group(0)
    assert "@192.168.0.60:5432/windmill?sslmode=require" in recipe and "helm " not in recipe, "shared PostgreSQL over TLS; Argo CD installs the chart"
    for target, guard in (("windmill-deploy", "WINDMILL_DEPLOY_APPROVED"), ("windmill-bootstrap", "WINDMILL_BOOTSTRAP_APPROVED")):
        assert f'test "$({guard})" = yes' in re.search(rf"^{target}:.*?(?=^\S)", make, re.M | re.S).group(0), target


def access_and_database():
    docs = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d]
    (route,) = [d for d in docs if d["kind"] == "IngressRoute"]
    (rule,) = route["spec"]["routes"]
    assert rule["match"] == f"Host(`{HOST}`)" and rule["middlewares"] == [{"name": "admin-lan"}] and route["spec"]["tls"] == {}
    assert rule["services"] == [{"name": "windmill-app", "port": 8000}]
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == "192.168.0.40"
    apps = {a["name"]: a for a in yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]}
    helpers = {r["name"]: r for r in apps["windmill"]["helper_roles"]}
    assert set(helpers) == {"windmill_user", "windmill_admin"} and helpers["windmill_admin"]["bypass_rls"] is True
    assert "bypass_rls" not in helpers["windmill_user"]


def scripts():
    """Scripts live in Git: each has its metadata, parses, and reads NetBox through the workspace variable only."""
    folder = ROOT / "windmill"
    sources = sorted(folder.glob("f/*/*.py"))
    assert sources, "at least one script"
    for source in sources:
        metadata = yaml.safe_load(source.with_suffix(".script.yaml").read_text())
        assert metadata["summary"] and metadata["description"], source
        text = source.read_text()
        tree = ast.parse(text)
        assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body), f"{source}: no main()"
        assert not re.search(r"nbt_[A-Za-z0-9]{6,}|Bearer [A-Za-z0-9]{20,}", text), f"{source}: a token in a script"
        if "netbox" in source.parts:
            assert 'wmill.get_variable("f/netbox/read_token")' in text and "netbox.doku-lab.net" not in text.replace(
                'NETBOX_URL = "https://netbox.doku-lab.net"', ""), source
            for call in re.findall(r"method=\"(\w+)\"", text):
                assert call == "GET", f"{source}: the inventory is only read"


def main():
    chart()
    access_and_database()
    scripts()
    print("PASS: Windmill chart pinned with single replicas, unprivileged workers, shared PostgreSQL over TLS, LAN-only route, "
          "helper roles without login, scripts in Git reading NetBox with the workspace token only")


if __name__ == "__main__":
    main()
