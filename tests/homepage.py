"""Offline fresh Homepage rendering, statelessness and scoped ownership guards."""
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]


def render(path):
    return list(yaml.safe_load_all(subprocess.check_output(
        ["kubectl", "kustomize", str(ROOT / path)], text=True
    )))


def main():
    app = render("gitops/stage-a/homepage")
    assert sorted(o["kind"] for o in app) == ["ConfigMap", "Deployment", "Service"]
    assert all(o["metadata"]["namespace"] == "homepage" for o in app)
    config = next(o for o in app if o["kind"] == "ConfigMap")
    assert set(config["data"]) == {
        "settings.yaml", "services.yaml", "bookmarks.yaml", "widgets.yaml",
        "kubernetes.yaml", "docker.yaml", "proxmox.yaml", "custom.css", "custom.js"
    }
    for name, value in config["data"].items():
        if name.endswith(".yaml"):
            yaml.safe_load(value)
    assert yaml.safe_load(config["data"]["kubernetes.yaml"]) == {"mode": "disabled"}
    assert yaml.safe_load(config["data"]["docker.yaml"]) == {}
    assert yaml.safe_load(config["data"]["proxmox.yaml"]) == {}
    deploy = next(o for o in app if o["kind"] == "Deployment")
    pod = deploy["spec"]["template"]["spec"]
    assert deploy["spec"]["replicas"] == 1
    assert pod["automountServiceAccountToken"] is False
    assert not any(k in pod for k in ("hostNetwork", "hostPID", "hostIPC", "nodeName", "nodeSelector", "affinity"))
    assert pod["securityContext"]["runAsNonRoot"]
    for v in pod["volumes"]:
        assert set(v) in ({"name", "configMap"}, {"name", "emptyDir"})
    assert next(v for v in pod["volumes"] if v["name"] == "config")["configMap"]["name"] == config["metadata"]["name"]
    c = pod["containers"][0]
    assert c["image"] == "ghcr.io/gethomepage/homepage:v2.4.0@sha256:643bd0be730d40f69d58028a55d1a896739333e8815786df42bc97f109ecbe61"
    assert c["securityContext"]["readOnlyRootFilesystem"]
    assert not c["securityContext"]["allowPrivilegeEscalation"]
    assert c["securityContext"]["capabilities"]["drop"] == ["ALL"]
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert c[probe]["httpGet"] == {"path": "/api/healthcheck", "port": "http"}
    env = {e["name"]: e.get("value") for e in c["env"]}
    assert env["LOG_TARGETS"] == "stdout"
    assert "*" not in env["HOMEPAGE_ALLOWED_HOSTS"] and "$(MY_POD_IP):3000" in env["HOMEPAGE_ALLOWED_HOSTS"]
    assert all("valueFrom" not in e or e["name"] == "MY_POD_IP" for e in c["env"])
    assert set(c["resources"]) == {"requests", "limits"}
    assert next(o for o in app if o["kind"] == "Service")["spec"]["type"] == "ClusterIP"
    bootstrap = render("gitops/stage-a/homepage-bootstrap")
    assert {o["kind"] for o in bootstrap} == {"Namespace", "ServiceAccount", "Role", "RoleBinding", "Kustomization"}
    role = next(o for o in bootstrap if o["kind"] == "Role" and o["metadata"]["namespace"] == "homepage")
    assert {r for rule in role["rules"] for r in rule["resources"]} == {"configmaps", "services", "deployments", "pods", "replicasets"}
    impersonation = next(o for o in bootstrap if o["kind"] == "Role" and o["metadata"]["namespace"] == "flux-system")
    assert impersonation["rules"] == [{"apiGroups": [""], "resources": ["serviceaccounts"], "resourceNames": ["homepage-reconciler"], "verbs": ["impersonate"]}]
    sync = next(o for o in bootstrap if o["kind"] == "Kustomization")
    assert sync["spec"]["path"] == "./gitops/stage-a/homepage"
    assert sync["spec"]["serviceAccountName"] == "homepage-reconciler"
    assert sync["spec"]["sourceRef"] == {"kind": "GitRepository", "name": "homelab-iac"}
    assert sync["spec"]["targetNamespace"] == "homepage" and sync["spec"]["prune"] and sync["spec"]["wait"]
    play = (ROOT / "ansible/playbooks/bootstrap-homepage.yml").read_text()
    assert "homepage_install_approved | default(false)" in play and "not ansible_check_mode" in play
    assert "Refuse adoption" in play and "k3s_node_names" in play
    denied = subprocess.run(["make", "homepage-install"], cwd=ROOT, capture_output=True, text=True)
    assert denied.returncode != 0 and "approval required" in denied.stdout
    print("PASS: Homepage render, pin/config, stateless restricted pod, scoped Flux RBAC and approval guards")


if __name__ == "__main__":
    main()
