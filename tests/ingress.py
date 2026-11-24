#!/usr/bin/env python3
"""Ingress certificates: render the pinned cert-manager chart and check issuer, certificate and Traefik store.

Needs `helm`, `openssl` and the chart download; no cluster access.
"""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/ingress"


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", (ROOT / "Makefile").read_text(), re.M)
    assert match, name
    return match.group(1).strip()


def legacy_routes():
    """Sites carried over from the legacy Caddy: every route has a Service and an address outside k3s."""
    docs = [d for d in yaml.safe_load_all((DIR / "legacy-routes.yaml").read_text()) if d]
    kinds = {}
    for d in docs:
        kinds.setdefault(d["kind"], {})[d["metadata"]["name"]] = d
    assert all(d["metadata"].get("namespace", "legacy-edge") == "legacy-edge" for d in docs if d["kind"] != "Namespace")
    services, slices = kinds["Service"], kinds["EndpointSlice"]
    assert set(services) == set(slices)
    for name, service in services.items():
        assert "selector" not in service["spec"], "backends are outside the cluster"
        (endpoint,) = slices[name]["endpoints"]
        (address,) = endpoint["addresses"]
        assert slices[name]["metadata"]["labels"] == {"kubernetes.io/service-name": name}
        assert slices[name]["ports"][0]["port"] == service["spec"]["ports"][0]["port"]
        assert re.fullmatch(r"192\.168\.0\.(13|15|2[0-9]|90)", address), f"{name}: legacy backend address expected, got {address}"
    hosts = set()
    for name, route in kinds["IngressRoute"].items():
        assert route["spec"]["entryPoints"] == ["websecure"] and route["spec"]["tls"] == {}, name
        for rule in route["spec"]["routes"]:
            hosts.update(re.findall(r"Host\(`([^`]+)`\)", rule["match"]))
            for ref in rule["services"]:
                assert ref["name"] in services and ref["port"] == services[ref["name"]]["spec"]["ports"][0]["port"]
                assert ("scheme" in ref) == ("serversTransport" in ref), "only HTTPS backends skip verification"
    assert all(h.endswith(".doku-lab.net") for h in hosts) and {"git.doku-lab.net", "cloud.doku-lab.net"} <= hosts and "vault.doku-lab.net" not in hosts
    assert "pve-lab.doku-lab.net" not in hosts, "stale Caddy sites are not carried over"
    assert slices["dropper"]["endpoints"][0]["addresses"] == ["192.168.0.90"], "the address reserved for VM 700, not a k3s node"
    # The public tunnel: one pinned connector, token from a Secret, nothing else granted.
    (tunnel,) = [d for d in yaml.safe_load_all((DIR / "tunnel.yaml").read_text()) if d and d["kind"] == "Deployment"]
    pod = tunnel["spec"]["template"]["spec"]
    (connector,) = pod["containers"]
    assert tunnel["spec"]["replicas"] == 1 and re.fullmatch(r"docker\.io/cloudflare/cloudflared:\d{4}\.\d+\.\d+", connector["image"])
    assert connector["env"] == [{"name": "TUNNEL_TOKEN", "valueFrom": {"secretKeyRef": {"name": "cloudflare-tunnel", "key": "token"}}}]
    assert pod["automountServiceAccountToken"] is False and pod["securityContext"]["runAsNonRoot"] is True
    assert connector["securityContext"]["readOnlyRootFilesystem"] is True and "--no-autoupdate" in connector["args"]
    assert "CLOUDFLARE_TUNNEL_TOKEN" in (ROOT / "Makefile").read_text()


def proxmox_routes():
    """Proxmox web interfaces: current host names, LAN only, backend certificate verified against the cluster CA."""
    docs = [d for d in yaml.safe_load_all((DIR / "proxmox-routes.yaml").read_text()) if d]
    expected = {"pve-management": "192.168.0.10", "pve-core": "192.168.0.11", "pve-infra": "192.168.0.12", "pve-lab": "192.168.0.16"}
    slices = {d["metadata"]["name"]: d["endpoints"][0]["addresses"] for d in docs if d["kind"] == "EndpointSlice"}
    assert slices == {name: [address] for name, address in expected.items()}, "never the old environment (192.168.0.14)"
    transports = {d["metadata"]["name"]: d["spec"] for d in docs if d["kind"] == "ServersTransport"}
    for name, address in expected.items():
        assert transports[name] == {"serverName": address, "rootCAs": [{"configMap": "doku-lab-cluster-ca"}]}, name
        assert "insecureSkipVerify" not in transports[name]
    (ca,) = [d for d in docs if d["kind"] == "ConfigMap"]
    repo_ca = "".join(l for l in (ROOT / "keys/pve-management-root-ca.crt").read_text().splitlines(keepends=True) if not l.startswith("#"))
    assert ca["data"]["ca.crt"] == repo_ca and "PRIVATE KEY" not in ca["data"]["ca.crt"]
    routes = {d["metadata"]["name"]: d["spec"] for d in docs if d["kind"] == "IngressRoute"}
    assert set(routes) == set(expected)
    for name, spec in routes.items():
        (rule,) = spec["routes"]
        assert spec["entryPoints"] == ["websecure"] and spec["tls"] == {} and rule["match"] == f"Host(`{name}.doku-lab.net`)"
        assert rule["middlewares"] == [{"name": "admin-lan"}]
        assert rule["services"] == [{"name": name, "port": 8006, "scheme": "https", "serversTransport": name}]


def main():
    version, repo = make_var("INGRESS_CERT_MANAGER_CHART"), make_var("INGRESS_CERT_MANAGER_REPO")
    assert re.fullmatch(r"v\d+\.\d+\.\d+", version), "the chart version is pinned"
    rendered = subprocess.run(
        ["helm", "template", "cert-manager", "cert-manager", "--repo", repo, "--version", version,
         "--namespace", "cert-manager", "-f", str(DIR / "cert-manager.yaml")], capture_output=True, text=True)
    assert rendered.returncode == 0, rendered.stderr
    docs = [d for d in yaml.safe_load_all(rendered.stdout) if d]
    deployments = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Deployment"}
    assert len(deployments) == 3, sorted(deployments)
    assert all(d["spec"]["replicas"] == 1 for d in deployments.values()), "single replicas for now"
    assert any(d["kind"] == "CustomResourceDefinition" for d in docs), "the chart installs its CRDs"
    args = deployments["cert-manager"]["spec"]["template"]["spec"]["containers"][0]["args"]
    assert "--dns01-recursive-nameservers-only" in args, "the LAN resolver rewrites doku-lab.net names"
    assert any(a.startswith("--dns01-recursive-nameservers=1.1.1.1:53") for a in args)
    assert not any(d["kind"] == "ServiceMonitor" for d in docs)

    issuer, certificate = yaml.safe_load_all((DIR / "certificates.yaml").read_text())
    acme = issuer["spec"]["acme"]
    assert issuer["kind"] == "ClusterIssuer" and acme["server"] == "https://acme-v02.api.letsencrypt.org/directory"
    (solver,) = acme["solvers"]
    assert solver["dns01"]["cloudflare"]["apiTokenSecretRef"] == {"name": "cloudflare-api-token", "key": "api-token"}
    assert solver["selector"]["dnsZones"] == ["doku-lab.net"] and "email" not in acme
    assert certificate["metadata"]["namespace"] == "kube-system", "next to Traefik's TLSStore"
    assert certificate["spec"]["dnsNames"] == ["*.doku-lab.net", "doku-lab.net"]
    assert certificate["spec"]["issuerRef"] == {"kind": "ClusterIssuer", "name": "letsencrypt"}

    store = yaml.safe_load((DIR / "tls-store.yaml").read_text())
    assert (store["metadata"]["name"], store["metadata"]["namespace"]) == ("default", "kube-system")
    assert store["spec"]["defaultCertificate"]["secretName"] == certificate["spec"]["secretName"]
    assert store["spec"]["certificates"] == [{"secretName": "ingress-default-tls"}], "sslip.io names keep their certificate"

    # The self-signed certificate the workstation trusts: a server certificate for the sslip.io names, not a CA.
    text = subprocess.run(["openssl", "x509", "-in", str(ROOT / "keys/k3s-ingress.crt"), "-noout", "-ext",
                           "subjectAltName,basicConstraints,extendedKeyUsage"], capture_output=True, text=True).stdout
    assert "DNS:*.192.168.0.40.sslip.io" in text and "CA:FALSE" in text and "TLS Web Server Authentication" in text

    legacy_routes()
    proxmox_routes()
    for path in DIR.glob("*.yaml"):
        assert not any(d and d.get("kind") == "Secret" for d in yaml.safe_load_all(path.read_text())), path
    makefile = (ROOT / "Makefile").read_text()
    for guard in ("INGRESS_CERTS_DEPLOY_APPROVED", "INGRESS_TLS_DEPLOY_APPROVED", "--from-env-file=<(printf 'api-token=%s"):
        assert guard in makefile, guard
    print("PASS: cert-manager pinned with single replicas, DNS-01 through Cloudflare with the token from a Secret, "
          "wildcard as Traefik's default, sslip.io certificate kept, no secret in Git")


if __name__ == "__main__":
    main()
