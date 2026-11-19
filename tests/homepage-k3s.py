#!/usr/bin/env python3
"""Dashboard on k3s (TASK-027): render services/homepage, check the pod, the route behind Authentik, that cards,
widgets and data sources name each other consistently, that nothing personal is in Git, and exercise the
widget data API on canned data.

Needs `kubectl` (for kustomize); no cluster, Proxmox or network access.
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/homepage"
HOST = "home.doku-lab.net"


def render():
    return [d for d in yaml.safe_load_all(subprocess.check_output(["kubectl", "kustomize", str(DIR)], text=True)) if d]


def config_digest():
    digest = hashlib.sha256()
    for path in sorted([*DIR.glob("config/*"), *DIR.glob("metrics/*")]):
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:16]


def load_server():
    spec = importlib.util.spec_from_file_location("homelab_metrics", DIR / "metrics/server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recipe(target):
    text = (ROOT / "Makefile").read_text()
    return re.search(rf"^{re.escape(target)}:.*\n((?:\t.*\n)+)", text, re.M).group(1)


def manifests():
    objects = render()
    kinds = sorted(o["kind"] for o in objects)
    assert kinds == ["ConfigMap", "ConfigMap", "Deployment", "IngressRoute", "Middleware", "Middleware", "Middleware",
                     "Namespace", "PersistentVolumeClaim", "Service"], kinds
    assert all(o["metadata"].get("namespace", "homepage") == "homepage" for o in objects)
    assert "Secret" not in kinds, "credentials and personal additions are written by make homepage-deploy, never from Git"
    (deployment,) = [o for o in objects if o["kind"] == "Deployment"]
    spec = deployment["spec"]
    assert spec["replicas"] == 1 and spec["strategy"] == {"type": "Recreate"}, "one replica; the image volume is mounted once"
    pod = spec["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False, "the dashboard gets no Kubernetes credentials"
    assert pod["securityContext"]["runAsNonRoot"] is True
    containers = {c["name"]: c for c in pod["containers"] + pod["initContainers"]}
    assert set(containers) == {"config", "homepage", "metrics"}
    for name, container in containers.items():
        assert re.search(r":v?\d+\.\d+\.\d+", container["image"]) and "latest" not in container["image"], f"{name}: pinned image"
        assert container["securityContext"]["allowPrivilegeEscalation"] is False and container["securityContext"]["capabilities"] == {"drop": ["ALL"]}
        if name != "config":
            assert container["resources"]["limits"]["memory"] and container["resources"]["requests"]["memory"], name
    homepage = containers["homepage"]
    assert {"name": "HOMEPAGE_ALLOWED_HOSTS", "value": HOST} in homepage["env"]
    assert containers["metrics"]["envFrom"] == [{"secretRef": {"name": "homepage-metrics", "optional": True}}], "the page starts without any credential"
    volumes = {v["name"]: v for v in pod["volumes"]}
    assert volumes["personal"]["secret"] == {"secretName": "homepage-personal", "optional": True}
    expected = config_digest()
    found = spec["template"]["metadata"]["annotations"]["homelab.doku-lab.net/config-digest"]
    assert found == expected, f"config/ or metrics/ changed: set config-digest in deployment.yaml to \"{expected}\" so the pod restarts"
    (claim,) = [o for o in objects if o["kind"] == "PersistentVolumeClaim"]
    assert claim["spec"]["storageClassName"] == "nvme-shared", "data lives on the NVMe-backed storage (ADR-012)"
    maps = {o["metadata"]["name"]: o for o in objects if o["kind"] == "ConfigMap"}
    assert set(maps["homepage-config"]["data"]) == {p.name for p in DIR.glob("config/*")}
    assert set(maps["homepage-metrics"]["data"]) == {p.name for p in DIR.glob("metrics/*")}
    return objects


def route(objects):
    middlewares = {o["metadata"]["name"]: o["spec"] for o in objects if o["kind"] == "Middleware"}
    assert middlewares["admin-lan"] == {"ipAllowList": {"sourceRange": ["192.168.0.0/24"]}}, "LAN only"
    assert middlewares["authentik"]["forwardAuth"]["address"].startswith("http://authentik-server.authentik.svc.cluster.local/outpost.goauthentik.io/")
    (ingress,) = [o for o in objects if o["kind"] == "IngressRoute"]
    assert ingress["spec"]["entryPoints"] == ["websecure"] and ingress["spec"]["tls"] == {}
    old, api, page = ingress["spec"]["routes"]
    assert old["match"] == "Host(`homepage.doku-lab.net`)" and {"name": "canonical-name"} in old["middlewares"]
    for rule in (api, page):
        assert rule["middlewares"] == [{"name": "admin-lan"}, {"name": "authentik"}], "nothing of the dashboard is served without a session"
    assert api["match"] == f"Host(`{HOST}`) && (Path(`/api/snapshot`) || PathPrefix(`/api/rdp/`))" and api["services"] == [{"name": "homepage", "port": 9101}]
    assert page["match"] == f"Host(`{HOST}`)" and page["services"] == [{"name": "homepage", "port": 3000}]
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    assert rewrites[HOST] == rewrites["homepage.doku-lab.net"] == "192.168.0.40", "both names reach Traefik"
    legacy = (ROOT / "services/ingress/legacy-routes.yaml").read_text()
    assert "homepage" not in legacy, "the route to the legacy container is gone: the name is served by services/homepage"
    application = yaml.safe_load((ROOT / "services/argocd/apps/homepage.yaml").read_text())
    assert application["spec"]["sources"][0]["path"] == "services/homepage"


def cards_and_widgets():
    """custom.js finds cards by id and data by key: every name it uses exists on the other side."""
    services = yaml.safe_load((DIR / "config/services.yaml").read_text())
    ids = [card[name]["id"] for group in services for cards in group.values() for card in cards for name in card]
    assert len(ids) == len(set(ids)), "card ids are unique"
    script = (DIR / "config/custom.js").read_text()
    sources = json.loads((DIR / "metrics/sources.json").read_text())

    def table(name):
        body = re.search(rf"var {name} = \{{(.*?)\}};", script, re.S).group(1)
        return dict(re.findall(r'"([\w-]+)": "(\w+)"', body))

    def listing(name):
        return re.findall(r'"([\w-]+)"', re.search(rf"var {name} = \[(.*?)\];", script, re.S).group(1))

    nodes, health = table("NODE_CARDS"), table("HEALTH_CARDS")
    node_keys = {spec["key"] for cluster in sources["proxmox"] for spec in cluster["nodes"].values()}
    assert set(nodes) <= set(ids) and set(nodes.values()) == node_keys, "one card per Proxmox node of sources.json"
    assert set(health) <= set(ids) and set(health.values()) <= set(sources["services"]), set(health.values()) - set(sources["services"])
    assert set(listing("TALL_CARDS")) <= set(ids)
    remote = {machine["card"] for machine in sources["remote"].values()}
    assert set(listing("REMOTE_CARDS")) == remote and remote <= set(ids)
    hrefs = {card[name]["id"]: card[name]["href"] for group in services for cards in group.values() for card in cards for name in card}
    for name, machine in sources["remote"].items():
        assert hrefs[machine["card"]] == f"/api/rdp/{name}", "the launcher is served by the widget API under the same name"
    assert [c["id"] for c in sources["proxmox"] if c.get("summary")] == ["doku-lab"], "the header sums the new cluster only"
    new = next(c for c in sources["proxmox"] if c["id"] == "doku-lab")
    assert new.get("verify", True) is True and (DIR / "metrics" / new["ca_file"]).read_text().startswith("-----BEGIN CERTIFICATE-----")
    assert all(e.startswith("https://192.168.0.14:") for c in sources["proxmox"] if c["id"] != "doku-lab" for e in c["endpoints"])
    assert "PRIVATE KEY" not in "".join(p.read_text() for p in DIR.glob("metrics/*"))
    # The page asks one address, on its own origin, with the visitor's session.
    assert re.findall(r'fetch\("([^"]+)"', script) == ["/api/snapshot"] and "192.168." not in script
    settings = yaml.safe_load((DIR / "config/settings.yaml").read_text())
    groups = [name for group in services for name in group]
    assert set(groups) <= set(settings["layout"]), "every group has a layout"
    # Nothing personal in a public repository: links and the weather location come from the Secret.
    public = "".join(p.read_text() for p in DIR.glob("config/*")).lower()
    for word in ("linkedin", "latitude", "openmeteo:", "gmail", "d2jsp"):
        assert word not in public, f"{word}: personal additions belong in the Secret homepage-personal"
    for name in ("bookmarks.yaml", "docker.yaml", "kubernetes.yaml", "proxmox.yaml", "widgets.yaml"):
        yaml.safe_load((DIR / "config" / name).read_text())
    assert yaml.safe_load((DIR / "config/kubernetes.yaml").read_text()) == {"mode": "disabled"}


def widget_api():
    server = load_server()
    sources = server.load_sources(DIR / "metrics/sources.json")
    cluster = sources["proxmox"][0]
    gib = 1024 ** 3
    resources = [
        {"type": "node", "node": "pve-core", "status": "online", "cpu": 0.25, "maxcpu": 16, "mem": 8 * gib, "maxmem": 32 * gib, "uptime": 90000},
        {"type": "node", "node": "pve-lab", "status": "offline"},
        {"type": "qemu", "node": "pve-core", "vmid": 311, "name": "k3s-server-02", "status": "running"},
        {"type": "qemu", "node": "pve-core", "vmid": 9000, "name": "template", "status": "stopped", "template": 1},
        {"type": "lxc", "node": "pve-core", "vmid": 120, "name": "ct", "status": "stopped"},
        {"type": "storage", "node": "pve-core", "storage": "local-lvm", "status": "available", "disk": 10 * gib, "maxdisk": 100 * gib},
        {"type": "storage", "node": "pve-core", "storage": "nfs", "shared": 1, "status": "available", "disk": 5 * gib, "maxdisk": 50 * gib},
        {"type": "storage", "node": "pve-infra", "storage": "nfs", "shared": 1, "status": "available", "disk": 5 * gib, "maxdisk": 50 * gib},
    ]
    nodes = server.proxmox_nodes(cluster, resources, {"pve-core": 0.5})
    core = nodes["pve_core"]
    assert (core["online"], core["cpu_percent"], core["cores"], core["load1"], core["ram_percent"]) == (True, 25.0, 16, 0.5, 25.0)
    assert (core["vms_running"], core["vms_total"], core["lxc_running"], core["lxc_total"]) == (1, 1, 0, 1), "templates are not guests"
    assert (core["storage_used_bytes"], core["storage_total_bytes"]) == (10 * gib, 100 * gib), "a node's storage is what it holds itself"
    assert nodes["pve_lab"]["online"] is False and nodes["pve_lab"]["error"] == "offline"
    assert nodes["pve_management"]["error"] == "not in the cluster"
    assert server.shared_storage(resources) == (5 * gib, 50 * gib), "shared storage is counted once"
    assert server.guest_states(resources)["311"]["status"] == "running"
    remote = server.remote_machines(sources, {"legacy": {"502": {"status": "running"}}})["services"]
    assert remote["win11-dev-service"]["running"] is True and remote["win11-game-service"]["status"] == "missing"

    postgres = server.postgres_members({"pg-01": 1, "pg-02": 1, "pg-03": 0}, {"pg-01": 0, "pg-02": 1, "pg-03": 0},
                                       {"pg-01": 0, "pg-02": 1000, "pg-03": 0}, {"pg-01": 900, "pg-02": 0, "pg-03": 400}, {"pg-02": 170012})
    assert (postgres["online"], postgres["leader"], postgres["members_running"], postgres["version"]) == (True, "pg-02", 2, "17.12")
    assert [m["lag_bytes"] for m in postgres["members"]] == [100, None, 600]
    assert server.postgres_members({}, {}, {}, {}, {})["online"] is False

    sessions = server.plex_sessions({"Metadata": [{"title": "Pilot", "grandparentTitle": "Show", "parentIndex": 1, "index": 2, "duration": 2000,
                                                   "viewOffset": 500, "User": {"title": "someone"}, "Player": {"title": "TV", "state": "playing"}}]})
    assert sessions == [{"title": "Pilot", "subtitle": "Show · S1E2", "user": "someone", "player": "TV", "state": "playing",
                         "elapsed_ms": 500, "duration_ms": 2000, "percent": 25.0}]
    assert server.rdp_file({"host": "192.168.0.51"}).startswith(b"full address:s:192.168.0.51\r\n")

    # Without credentials every source says so and nothing is contacted.
    for name in ("PVE_TOKEN", "PVE_LEGACY_TOKEN", "TRUENAS_API_KEY", "PLEX_TOKEN", "QBIT_USERNAME", "QBIT_PASSWORD"):
        server.os.environ.pop(name, None)

    def no_network(*_args, **_kwargs):
        raise AssertionError("a source without its credential must not be contacted")

    server.fetch = no_network
    state = server.State()
    server.collect_proxmox(state, sources)
    server.collect_truenas(state, sources)
    server.collect_plex(state, sources)
    server.Qbit().collect(state, sources)
    snapshot = state.snapshot()
    assert all(node["error"] == "not connected yet" for node in snapshot["nodes"].values()) and len(snapshot["nodes"]) == 5
    assert snapshot["truenas"] == snapshot["plex"] == snapshot["qbit"] == {"configured": False}
    assert snapshot["summary"]["compute"]["cores"] == 0

    # The server answers three kinds of address and nothing else, and never anything but GET.
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(state, sources))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base}/api/snapshot", timeout=5) as response:
            assert set(json.load(response)) >= {"nodes", "summary", "remote", "meta"}
        with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"{base}/api/rdp/win11-dev", timeout=5) as response:
            assert response.headers["Content-Type"] == "application/x-rdp" and b"192.168.0.51" in response.read()
        for path, method in (("/api/rdp/unknown", "GET"), ("/etc/passwd", "GET"), ("/api/snapshot", "POST")):
            try:
                urllib.request.urlopen(urllib.request.Request(base + path, method=method, data=b"" if method == "POST" else None), timeout=5)
                raise AssertionError(f"{method} {path} must be refused")
            except urllib.error.HTTPError as error:
                assert error.code in (404, 501), (path, error.code)
    finally:
        httpd.shutdown()
    text = (DIR / "metrics/server.py").read_text()
    assert "do_POST" not in text and "do_PUT" not in text and "do_DELETE" not in text
    for line in text.splitlines():
        assert not re.search(r"print\(.*(token|password|key)", line, re.I), "credentials are never printed"


def make_targets():
    deploy = recipe("homepage-deploy")
    assert 'test "$(HOMEPAGE_DEPLOY_APPROVED)" = yes' in deploy and "--from-env-file=<(" in deploy and "helm " not in deploy
    assert "homepage-metrics" in deploy and "homepage-personal" in deploy and "services/argocd/apps/homepage.yaml" in deploy
    token = recipe("homepage-pve-token")
    assert 'test "$(HOMEPAGE_PVE_TOKEN_APPROVED)" = yes' in token and "--roles PVEAuditor" in token, "read-only, and only when approved"
    assert "scripts/secrets.py set /homepage" in token and "echo $$" not in token
    assert 'test "$(HOMEPAGE_DEPLOY_APPROVED)" = yes' in recipe("homepage-images")
    ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", ".local/homepage/images/x.png"]).returncode
    assert ignored == 0, "background images and personal additions stay outside Git"


def main():
    objects = manifests()
    route(objects)
    cards_and_widgets()
    widget_api()
    make_targets()
    print("PASS: dashboard with one replica, no Kubernetes credentials, pinned images and optional secrets; LAN-only route with "
          "Authentik on every path; cards, widgets and data sources agree; nothing personal in Git; widget API read-only and "
          "correct on canned data")


if __name__ == "__main__":
    main()
