"""Offline Flux/demo render and ownership guards. No API, credentials or Git writes."""

import hashlib
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]


def render(path):
    output = subprocess.check_output(["kubectl", "kustomize", str(ROOT / path)], text=True)
    return list(yaml.safe_load_all(output))


def main():
    vendor = ROOT / "gitops/stage-a/bootstrap/gotk-components.yaml"
    assert hashlib.sha256(vendor.read_bytes()).hexdigest() == "ce5ceb48517b29660e493a164f8e22956e4b1e62165989add30829f587d8cb5f"
    bootstrap = render("gitops/stage-a/bootstrap")
    assert not any(o["kind"] in ("ClusterRole", "ClusterRoleBinding", "Secret") for o in bootstrap)
    controllers = [o for o in bootstrap if o["kind"] == "Deployment"]
    assert {o["metadata"]["name"] for o in controllers} == {"source-controller", "kustomize-controller"}
    for obj in controllers:
        container = obj["spec"]["template"]["spec"]["containers"][0]
        assert container["image"] == f"ghcr.io/fluxcd/{obj['metadata']['name']}:v1.9.5"
        assert "--watch-all-namespaces=false" in container["args"]
        if obj["metadata"]["name"] == "kustomize-controller":
            for arg in ("--no-remote-bases=true", "--no-cross-namespace-refs=true", "--default-service-account=default"):
                assert arg in container["args"]
    roles = [o for o in bootstrap if o["kind"] == "Role"]
    demo_role = next(o for o in roles if o["metadata"]["name"] == "demo-reconciler")
    assert demo_role["metadata"]["namespace"] == "flux-demo"
    assert {r for rule in demo_role["rules"] for r in rule["resources"]} == {"configmaps", "services", "deployments", "pods", "replicasets"}
    impersonation = next(o for o in roles if o["metadata"]["name"] == "demo-impersonation")
    assert impersonation["rules"] == [{"apiGroups": [""], "resources": ["serviceaccounts"], "resourceNames": ["demo-reconciler", "default"], "verbs": ["impersonate"]}]
    source, sync = yaml.safe_load_all((ROOT / "gitops/stage-a/source.yaml").read_text())
    assert source["spec"]["url"] == "https://git.doku-lab.net/Homelab/homelab-iac.git"
    assert source["spec"]["ref"] == {"branch": "main"} and "secretRef" not in source["spec"]
    assert sync["spec"]["path"] == "./gitops/stage-a/demo"
    assert sync["spec"]["serviceAccountName"] == "demo-reconciler"
    assert sync["spec"]["targetNamespace"] == "flux-demo"
    assert sync["spec"]["prune"] and sync["spec"]["wait"]
    demo = render("gitops/stage-a/demo")
    assert sorted(o["kind"] for o in demo) == ["ConfigMap", "Deployment", "Service"]
    assert all(o["metadata"]["namespace"] == "flux-demo" for o in demo)
    deploy = next(o for o in demo if o["kind"] == "Deployment")
    pod = deploy["spec"]["template"]["spec"]
    assert deploy["spec"]["replicas"] == 2 and pod["automountServiceAccountToken"] is False
    assert not any(k in pod for k in ("hostNetwork", "hostPID", "hostIPC"))
    assert all(set(v) == {"name", "configMap"} for v in pod["volumes"])
    c = pod["containers"][0]
    assert "@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e" in c["image"]
    assert c["securityContext"]["readOnlyRootFilesystem"] and not c["securityContext"]["allowPrivilegeEscalation"]
    assert c["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert "readinessProbe" in c and "livenessProbe" in c
    assert next(o for o in demo if o["kind"] == "Service")["spec"]["type"] == "ClusterIP"
    play = (ROOT / "ansible/playbooks/bootstrap-flux.yml").read_text()
    assert "flux_install_approved | default(false)" in play and "not ansible_check_mode" in play
    assert "delegate_to: localhost" in play and "k3s_init_host" in play
    assert "get, nodes" in play and "Refuse to adopt" in play
    make = subprocess.run(["make", "flux-install"], cwd=ROOT, capture_output=True, text=True)
    assert make.returncode != 0 and "approval required" in make.stdout
    print("PASS: Flux pin/render, scoped RBAC, anonymous source, disposable app and approval guards")


if __name__ == "__main__":
    main()
