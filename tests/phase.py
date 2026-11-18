#!/usr/bin/env python3
"""Phase Console (M008): render the pinned official chart with our values and check database, routes and secrets.

Needs `helm` and the chart download; no cluster access.
"""
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = "phase.192.168.0.40.sslip.io"


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


# Shapes copied from the v2.79.0 frontend bundle; the third line is unrelated code that must not change.
BUNDLE = (
    'if(v!==x)return void g.toast.error("Passwords don\'t match");if(v.length<16)return void g.toast.error('
    '"Password must be at least 16 characters");A(!0)\n'
    '(0,b.jsx)(d.f,{id:"password",label:"Password",value:v,setValue:w,secret:!0,required:!0,minLength:16})\n'
    'if(a.length<16||a.length>32||a.length%4!=0)throw TypeError(d)\n'
    'u=o.length>=16,h=t?.feedback?.suggestions??[],g=u?h:[`Use at least 16 characters (currently ${o.length})`,...h]\n')


def password_policy():
    patch = yaml.safe_load((ROOT / "services/phase/frontend-password-policy.yaml").read_text())
    (container,) = patch["spec"]["template"]["spec"]["containers"]
    assert container["name"] == "frontend" and container["command"] == ["/bin/bash", "-euc"]
    (script,) = container["args"]
    assert "$(" not in script, "Kubernetes would try to expand $(NAME) in container arguments"
    assert script.rstrip().endswith("exec /app/scripts/start.sh"), "the unchanged start script runs last"

    def run(content):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "static" / "chunk.js"
            target.parent.mkdir()
            target.write_text(content)
            local = script.replace("root=/app/.next", f"root={tmp}").replace("exec /app/scripts/start.sh", "echo started")
            assert local != script
            result = subprocess.run(["bash", "-euc", local], capture_output=True, text=True)
            return result, target.read_text()

    result, text = run(BUNDLE)
    assert result.returncode == 0 and result.stdout.strip() == "started", result.stderr
    assert 'v.length<10)return void g.toast.error("Password must be at least 10 characters")' in text
    assert "minLength:10}" in text and "o.length>=10,h=" in text and "Use at least 10 characters (currently" in text
    assert "a.length<16||a.length>32" in text, "unrelated length checks stay as they are"
    assert "16 characters" not in text and "minLength:16" not in text
    # A Console version without the known code, or with a changed shape, stops the container instead of starting.
    for changed in ("console.log(1)\n", BUNDLE.replace("v.length<16)return void", "v.length<16)return")):
        result, _ = run(changed)
        assert result.returncode != 0 and "started" not in result.stdout and "review" in result.stderr


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
    assert "patch deployment phase-console-frontend --patch-file services/phase/frontend-password-policy.yaml" in deploy
    assert deploy.index("helm upgrade") < deploy.index("frontend-password-policy.yaml"), "the patch follows the chart"
    password_policy()
    print("PASS: Phase chart and Console pinned, external TLS database, no in-cluster database, "
          "HTTPS + admin-LAN routes, secrets only from the environment, 10-character password rule fails closed")


if __name__ == "__main__":
    main()
