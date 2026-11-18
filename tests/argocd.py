#!/usr/bin/env python3
"""Argo CD (M009): render the pinned official chart with our values and check route, project and applications.

Needs `helm` and the chart download; no cluster access.
"""
import base64
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/argocd"
HOST = "argocd.doku-lab.net"
REPO = "https://git.doku-lab.net/Homelab/homelab-iac.git"
CLUSTER = "https://kubernetes.default.svc"


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def chart():
    result = subprocess.run(["helm", "template", "argocd", "argo-cd", "--repo", make_var("ARGOCD_REPO"), "--version",
                             make_var("ARGOCD_CHART_VERSION"), "--namespace", "argocd", "-f", str(DIR / "values.yaml")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    workloads = {d["metadata"]["name"]: d for d in docs if d["kind"] in ("Deployment", "StatefulSet")}
    assert set(workloads) == {"argocd-application-controller", "argocd-server", "argocd-repo-server", "argocd-redis",
                              "argocd-applicationset-controller"}, "no single sign-on, no notifications"
    for name, workload in workloads.items():
        expected = 0 if name == "argocd-applicationset-controller" else 1
        assert workload["spec"]["replicas"] == expected, f"{name}: one replica per service for now"
        pod = workload["spec"]["template"]["spec"]
        for container in pod.get("initContainers", []) + pod["containers"]:
            assert re.search(r":v?\d+\.\d+\.\d+", container["image"]) and not container["image"].endswith(":latest"), container["image"]
    for name in ("argocd-application-controller", "argocd-server", "argocd-repo-server", "argocd-redis"):
        assert workloads[name]["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["memory"], name
    maps = {d["metadata"]["name"]: d.get("data") or {} for d in docs if d["kind"] == "ConfigMap"}
    assert maps["argocd-cmd-params-cm"]["server.insecure"] == "true", "TLS ends at Traefik"
    assert maps["argocd-cm"]["exec.enabled"] == "false" and maps["argocd-cm"]["url"] == f"https://{HOST}"
    # Repository entries are rendered as Secrets by the chart: they must carry addresses only, no credentials.
    repositories = [d for d in docs if d["kind"] == "Secret" and d["metadata"].get("labels", {}).get("argocd.argoproj.io/secret-type") == "repository"]
    assert len(repositories) == 1
    for repository in repositories:
        assert set(repository["data"]) == {"name", "type", "url", "enableOCI"}, repository["data"].keys()
    assert not [d for d in docs if d["kind"] in ("Ingress", "HTTPRoute")], "the route is in access.yaml"
    return {base64.b64decode(r["data"]["url"]).decode() for r in repositories}


def access_and_applications(registries):
    docs = [d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d]
    assert all(d["metadata"]["namespace"] == "argocd" for d in docs) and "Secret" not in [d["kind"] for d in docs]
    (route,) = [d for d in docs if d["kind"] == "IngressRoute"]
    (rule,) = route["spec"]["routes"]
    assert rule["match"] == f"Host(`{HOST}`)" and rule["middlewares"] == [{"name": "admin-lan"}] and route["spec"]["tls"] == {}
    assert rule["services"] == [{"name": "argocd-server", "port": 80}] and route["spec"]["entryPoints"] == ["websecure"]
    (lan,) = [d for d in docs if d["kind"] == "Middleware"]
    assert lan["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"]
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == "192.168.0.40"

    (project,) = [d for d in docs if d["kind"] == "AppProject"]
    spec = project["spec"]
    assert REPO in spec["sourceRepos"] and "*" not in spec["sourceRepos"], "only this repository and the listed chart registries"
    assert set(spec["sourceRepos"]) - {REPO} == registries, "every chart registry of the project is declared to Argo CD"
    assert all(d["server"] == CLUSTER and d["namespace"] != "*" for d in spec["destinations"]), "this cluster, named namespaces"
    assert spec["clusterResourceWhitelist"] == [{"group": "", "kind": "Namespace"}], "no cluster-wide objects beyond namespaces"
    namespaces = {d["namespace"] for d in spec["destinations"]}
    assert "argocd" not in namespaces and "kube-system" not in namespaces, "applications cannot change Argo CD or the system"

    applications = sorted((DIR / "apps").glob("*.yaml"))
    assert applications
    for path in applications:
        (application,) = [d for d in yaml.safe_load_all(path.read_text()) if d]
        app = application["spec"]
        assert application["kind"] == "Application" and application["metadata"] == {"name": path.stem, "namespace": "argocd"}
        assert app["project"] == "platform" and app["destination"] == {"server": CLUSTER, "namespace": path.stem}
        assert app["destination"]["namespace"] in namespaces
        assert app["syncPolicy"]["automated"] == {"prune": False, "selfHeal": True}, "nothing is deleted automatically"
        for source in app["sources"]:
            assert source["repoURL"] in spec["sourceRepos"], source["repoURL"]
            if "chart" in source:
                assert re.fullmatch(r"\d+\.\d+\.\d+", source["targetRevision"]), "charts are pinned"
                for values in source["helm"]["valueFiles"]:
                    assert values.startswith("$values/") and (ROOT / values[len("$values/"):]).is_file(), values
            else:
                assert source["repoURL"] == REPO and source["targetRevision"] == "main"
                if "path" in source:
                    # Argo CD applies these files as they are: they must exist and hold no Secret.
                    included = ROOT / source["path"] / source["directory"]["include"]
                    kinds = [d["kind"] for d in yaml.safe_load_all(included.read_text()) if d]
                    assert kinds and "Secret" not in kinds, included


def make_guards():
    make = (ROOT / "Makefile").read_text()
    for target, guard in (("argocd-deploy", "ARGOCD_DEPLOY_APPROVED"), ("argocd-password", "ARGOCD_PASSWORD_APPROVED")):
        recipe = re.search(rf"^{target}:.*?(?=^\S)", make, re.M | re.S).group(0)
        assert f'test "$({guard})" = yes' in recipe, target
        refused = subprocess.run(["make", "-C", str(ROOT), target], capture_output=True, text=True)
        assert refused.returncode != 0 and "Approve" in refused.stderr + refused.stdout, target
    password = re.search(r"^argocd-password:.*?(?=^\S)", make, re.M | re.S).group(0)
    assert "scripts/secrets.py set /argocd" in password and "echo \"$$(" not in password, "the password goes to the store, not the screen"


def main():
    registries = chart()
    access_and_applications(registries)
    make_guards()
    print("PASS: Argo CD chart pinned with single replicas, LAN-only route behind Traefik, no credentials in Git, "
          "project limited to this repository, this cluster and named namespaces, applications pinned and never pruning")


if __name__ == "__main__":
    main()
