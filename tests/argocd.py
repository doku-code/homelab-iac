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
    assert maps["argocd-cm"]["kustomize.buildOptions"] == "--enable-helm", "services/phase renders a chart through kustomize"
    excluded = {kind for entry in yaml.safe_load(maps["argocd-cm"]["resource.exclusions"]) for kind in entry["kinds"]}
    assert "EndpointSlice" not in excluded and {"Endpoints", "Lease"} <= excluded, "the routes to outside services need EndpointSlices"
    # Repository entries are rendered as Secrets by the chart: they must carry addresses only, no credentials.
    repositories = [d for d in docs if d["kind"] == "Secret" and d["metadata"].get("labels", {}).get("argocd.argoproj.io/secret-type") == "repository"]
    assert len(repositories) == 1
    for repository in repositories:
        assert set(repository["data"]) == {"name", "type", "url", "enableOCI"}, repository["data"].keys()
    assert not [d for d in docs if d["kind"] in ("Ingress", "HTTPRoute")], "the route is in access.yaml"
    return {base64.b64decode(r["data"]["url"]).decode() for r in repositories}


# Chart pins also used by the offline tests of each service: release -> Makefile variables (repository, version).
PINS = {
    "headlamp": ("HEADLAMP_REPO", "HEADLAMP_CHART_VERSION"),
    "prometheus": ("OBS_PROMETHEUS_REPO", "OBS_PROMETHEUS_CHART"),
    "loki": ("OBS_GRAFANA_LABS_REPO", "OBS_LOKI_CHART"),
    "alloy": ("OBS_GRAFANA_LABS_REPO", "OBS_ALLOY_CHART"),
    "grafana": ("OBS_GRAFANA_REPO", "OBS_GRAFANA_CHART"),
    "cert-manager": ("INGRESS_CERT_MANAGER_REPO", "INGRESS_CERT_MANAGER_CHART"),
    "csi-driver-nfs": ("STORAGE_CSI_REPO", "STORAGE_CSI_CHART_VERSION"),
    "phase-console": ("PHASE_REPO", "PHASE_CHART_VERSION"),
}


def applied_files(path, source):
    """The files Argo CD applies as they are from a Git path: a kustomization, or the included manifests."""
    if (path / "kustomization.yaml").exists():
        assert "directory" not in source
        kustomization = yaml.safe_load((path / "kustomization.yaml").read_text())
        for chart in kustomization.get("helmCharts", []):
            repo, version = PINS[chart["releaseName"]]
            assert (chart["repo"], chart["version"]) == (make_var(repo), make_var(version)), chart["releaseName"]
            assert (path / chart["valuesFile"]).is_file()
        for generator in kustomization.get("configMapGenerator", []):
            for entry in generator["files"]:
                assert (path / entry.split("=")[-1]).is_file(), entry
        for patch in kustomization.get("patches", []):
            assert (path / patch["path"]).is_file()
        return [path / name for name in kustomization["resources"]]
    names = source["directory"]["include"].strip("{}").split(",")
    return [path / name for name in names]


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

    projects = {d["metadata"]["name"]: d["spec"] for d in docs if d["kind"] == "AppProject"}
    assert set(projects) == {"platform", "infrastructure"}
    namespaces = {}
    for name, spec in projects.items():
        assert REPO in spec["sourceRepos"] and "*" not in spec["sourceRepos"], "only this repository and the listed chart registries"
        assert all(d["server"] == CLUSTER and d["namespace"] != "*" for d in spec["destinations"]), "this cluster, named namespaces"
        namespaces[name] = {d["namespace"] for d in spec["destinations"]}
        assert "argocd" not in namespaces[name], "no application can change Argo CD itself"
    assert not namespaces["platform"] & namespaces["infrastructure"], "a namespace belongs to one project"
    # Ordinary services cannot touch the system namespace or create cluster-wide objects beyond their own roles.
    assert "kube-system" not in namespaces["platform"]
    assert projects["platform"]["clusterResourceWhitelist"] == [
        {"group": "", "kind": "Namespace"}, {"group": "rbac.authorization.k8s.io", "kind": "ClusterRole"},
        {"group": "rbac.authorization.k8s.io", "kind": "ClusterRoleBinding"},
        {"group": "apiextensions.k8s.io", "kind": "CustomResourceDefinition"}]
    oci = {repo for spec in projects.values() for repo in spec["sourceRepos"] if "://" not in repo}
    assert oci == registries, "every OCI chart registry of a project is declared to Argo CD"

    applications = sorted((DIR / "apps").glob("*.yaml"))
    assert {p.stem for p in applications} == {"netbox", "headlamp", "monitoring", "phase", "ingress", "storage"}
    used_repos, used_namespaces = set(), set()
    for path in applications:
        (application,) = [d for d in yaml.safe_load_all(path.read_text()) if d]
        app = application["spec"]
        assert application["kind"] == "Application" and application["metadata"] == {"name": path.stem, "namespace": "argocd"}
        project = projects[app["project"]]
        assert app["destination"]["server"] == CLUSTER and app["destination"]["namespace"] in namespaces[app["project"]], path.stem
        used_namespaces.add(app["destination"]["namespace"])
        assert app["syncPolicy"]["automated"] == {"prune": False, "selfHeal": True}, "nothing is deleted automatically"
        for source in app["sources"]:
            assert source["repoURL"] in project["sourceRepos"], source["repoURL"]
            used_repos.add(source["repoURL"])
            if "chart" in source:
                assert re.fullmatch(r"v?\d+\.\d+\.\d+", source["targetRevision"]), "charts are pinned"
                release = source["helm"]["releaseName"]
                if release in PINS:
                    repo, version = PINS[release]
                    assert (source["repoURL"], source["targetRevision"]) == (make_var(repo), make_var(version)), release
                for values in source["helm"]["valueFiles"]:
                    assert values.startswith("$values/") and (ROOT / values[len("$values/"):]).is_file(), values
            else:
                assert source["repoURL"] == REPO and source["targetRevision"] == "main"
                if "path" in source:
                    for applied in applied_files(ROOT / source["path"], source):
                        objects = [d for d in yaml.safe_load_all(applied.read_text()) if d]
                        assert objects, applied
                        for item in objects:
                            # A Secret in Git may only be an empty shell Kubernetes fills in (a service-account token).
                            assert item["kind"] != "Secret" or not (item.get("data") or item.get("stringData")), applied
                            namespace = item["metadata"].get("namespace")
                            assert namespace is None or namespace in namespaces[app["project"]], f"{applied}: {namespace}"
    assert used_repos == {repo for spec in projects.values() for repo in spec["sourceRepos"]}, "no unused source in a project"
    dashboards = {p.name for p in (ROOT / "services/observability/dashboards").glob("*.json")}
    generated = yaml.safe_load((ROOT / "services/observability/kustomization.yaml").read_text())["configMapGenerator"]
    listed = {Path(f).name for g in generated if g["name"] == "grafana-dashboards" for f in g["files"]}
    assert listed == dashboards, "every dashboard file is listed in the kustomization"


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
          "two projects limited to this repository, this cluster and named namespaces, six applications pinned and never pruning")


if __name__ == "__main__":
    main()
