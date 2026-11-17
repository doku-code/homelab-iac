#!/usr/bin/env python3
"""Phase Console (M008): render the pinned official chart with our values and check database, routes and secrets.

Needs `helm` and the chart download; no cluster access.
"""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = "phase.192.168.0.40.sslip.io"


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def main():
    version, repo = make_var("PHASE_CHART_VERSION"), make_var("PHASE_REPO")
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "the chart version is pinned"
    values = yaml.safe_load((ROOT / "services/phase/values.yaml").read_text())
    assert re.fullmatch(r"v\d+\.\d+\.\d+", values["global"]["version"]), "the Console version is pinned, never latest"
    rendered = subprocess.run(
        ["helm", "template", "phase-console", "phase", "--repo", repo, "--version", version, "--namespace", "phase",
         "-f", str(ROOT / "services/phase/values.yaml")], capture_output=True, text=True)
    assert rendered.returncode == 0, rendered.stderr
    docs = [d for d in yaml.safe_load_all(rendered.stdout) if d]
    kinds = [d["kind"] for d in docs]
    assert "StatefulSet" not in kinds and "PersistentVolumeClaim" not in kinds, "no database inside the cluster"
    assert "Ingress" not in kinds, "the ingress-nginx Ingress is replaced by services/phase/access.yaml"
    config = next(d for d in docs if d["kind"] == "ConfigMap")["data"]
    assert config["HOST"] == HOST and config["HTTP_PROTOCOL"] == "https://"
    assert (config["DATABASE_HOST"], config["DATABASE_NAME"], config["DATABASE_USER"]) == ("192.168.0.60", "phase", "phase")
    assert config["DATABASE_SSL"] == "True", "the shared PostgreSQL accepts TLS only"
    images = set(re.findall(r'image: "?([^"\s]+)', rendered.stdout))
    assert {i for i in images if "phasehq/" in i} == {
        f"docker.io/phasehq/backend:{values['global']['version']}", f"docker.io/phasehq/frontend:{values['global']['version']}"}
    assert "secretKeyRef" in rendered.stdout and "phase-console-secret" in rendered.stdout
    names = {d["metadata"]["name"] for d in docs if d["kind"] == "Service"}
    assert {"phase-console-backend", "phase-console-frontend"} <= names

    # The application "phase" exists on the shared PostgreSQL platform under the same name as its role.
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert {"name": "phase"} in apps

    access = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((ROOT / "services/phase/access.yaml").read_text())}
    assert access[("Middleware", "admin-lan")]["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"]
    assert access[("Middleware", "strip-service")]["spec"]["stripPrefix"]["prefixes"] == ["/service"]
    route = access[("IngressRoute", "phase-console")]["spec"]
    assert route["entryPoints"] == ["websecure"] and route["tls"] == {}, "HTTPS only"
    backend, frontend = route["routes"]
    assert backend["match"] == f"Host(`{HOST}`) && (Path(`/service`) || PathPrefix(`/service/`))"
    assert [m["name"] for m in backend["middlewares"]] == ["admin-lan", "strip-service"]
    assert backend["services"] == [{"name": "phase-console-backend", "port": 8000}]
    assert frontend["match"] == f"Host(`{HOST}`)" and [m["name"] for m in frontend["middlewares"]] == ["admin-lan"]
    assert frontend["services"] == [{"name": "phase-console-frontend", "port": 3000}]
    assert all(d["metadata"].get("namespace", "phase") == "phase" for d in access.values() if d["kind"] != "Namespace")
    assert not any(d["kind"] == "Secret" for d in access.values()), "no secret values in Git"

    makefile = (ROOT / "Makefile").read_text()
    assert "PHASE_DEPLOY_APPROVED" in makefile and "--from-env-file=<(printf" in makefile
    deploy = makefile[makefile.index("phase-deploy:"):]
    deploy = deploy[:deploy.index("\n\n")]
    assert "--wait" not in deploy, "the migration job is a post-install hook: helm --wait would deadlock on it"
    print("PASS: Phase chart and Console pinned, external TLS database, no in-cluster database, "
          "HTTPS + admin-LAN routes, secrets only from the environment")


if __name__ == "__main__":
    main()
