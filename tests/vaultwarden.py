#!/usr/bin/env python3
"""Offline checks of the Vaultwarden deployment (TASK-032): pinned image, one replica, vault in the shared
PostgreSQL, no secret in Git, nobody can register, LAN-only route, guarded Make targets."""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/vaultwarden"


def main():
    text = (DIR / "vaultwarden.yaml").read_text()
    docs = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all(text) if d}
    deployment = docs[("Deployment", "vaultwarden")]["spec"]
    pod = deployment["template"]["spec"]
    (container,) = pod["containers"]
    assert deployment["replicas"] == 1 and deployment["strategy"]["type"] == "Recreate"
    assert re.fullmatch(r"docker\.io/vaultwarden/server:\d+\.\d+\.\d+", container["image"]), "pinned release, never latest"
    env = {e["name"]: e for e in container["env"]}
    assert env["DOMAIN"]["value"] == "https://vault.doku-lab.net"
    assert env["SIGNUPS_ALLOWED"]["value"] == "false" and env["INVITATIONS_ALLOWED"]["value"] == "false"
    assert env["DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {"name": "vaultwarden-secrets", "key": "database-url"}
    assert "ADMIN_TOKEN" not in env, "the administration page stays off"
    assert not any(kind == "Secret" for kind, _ in docs) and "postgresql://" not in text, "no secret values in Git"
    assert pod["securityContext"]["runAsNonRoot"] is True and pod["automountServiceAccountToken"] is False
    assert container["securityContext"]["readOnlyRootFilesystem"] is True and container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert set(container["resources"]) == {"requests", "limits"}
    claim = docs[("PersistentVolumeClaim", "vaultwarden-data")]["spec"]
    assert claim["storageClassName"] == "nvme-shared", "user data on the NVMe-backed storage, not on a node"
    route = docs[("IngressRoute", "vaultwarden")]["spec"]
    (rule,) = route["routes"]
    assert route["entryPoints"] == ["websecure"] and route["tls"] == {} and rule["match"] == "Host(`vault.doku-lab.net`)"
    assert [m["name"] for m in rule["middlewares"]] == ["admin-lan", "hsts"]
    assert docs[("Middleware", "admin-lan")]["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24", "10.42.0.0/16"]
    assert rule["services"] == [{"name": "vaultwarden", "port": 8080}]

    # The old route to the container on the old host is gone: one owner of the name.
    legacy = (ROOT / "services/ingress/legacy-routes.yaml").read_text()
    assert "vault.doku-lab.net" not in legacy and "192.168.0.26" not in legacy

    application = yaml.safe_load((ROOT / "services/argocd/apps/vaultwarden.yaml").read_text())["spec"]
    assert application["project"] == "platform" and application["destination"]["namespace"] == "vaultwarden"
    assert application["syncPolicy"]["automated"] == {"prune": False, "selfHeal": True}
    projects = [d for d in yaml.safe_load_all((ROOT / "services/argocd/access.yaml").read_text()) if d and d["kind"] == "AppProject"]
    platform = next(p for p in projects if p["metadata"]["name"] == "platform")
    assert {"server": "https://kubernetes.default.svc", "namespace": "vaultwarden"} in platform["spec"]["destinations"]
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert {"name": "vaultwarden"} in apps

    for target, variable in (("vaultwarden-secrets", "VAULTWARDEN_SECRETS_APPROVED"), ("vaultwarden-deploy", "VAULTWARDEN_DEPLOY_APPROVED")):
        result = subprocess.run(["make", "--no-print-directory", target], cwd=ROOT, capture_output=True, text=True,
                                env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        assert result.returncode != 0 and variable in result.stderr, target
    print("PASS: Vaultwarden pinned with one replica, vault in the shared PostgreSQL, no secret in Git, registration off, LAN-only route")


if __name__ == "__main__":
    main()
