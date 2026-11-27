#!/usr/bin/env python3
"""Widget data for the dashboard: one JSON snapshot that custom.js draws (TASK-027).

  GET /health          liveness and the age of each collector's data
  GET /api/snapshot    everything the widgets show
  GET /api/rdp/<name>  an .rdp launcher for a machine of sources.json

Standard library only, so it runs on a stock Python image with this file mounted. What to watch is in
sources.json (Git); credentials come from the environment and each one is optional: a source without its
credential reports "configured": false and the page says so instead of failing. Everything is read-only.

  PVE_TOKEN, PVE_LEGACY_TOKEN      Proxmox API tokens with the PVEAuditor role ("user@realm!name=value")
  PLEX_TOKEN                       Plex token
  QBIT_USERNAME, QBIT_PASSWORD     qBittorrent web login
"""
import http.cookiejar
import functools
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMEOUT = 8
SERIES_POINTS = 240


def load_sources(path=None):
    return json.loads(Path(path or os.environ.get("SOURCES_FILE", HERE / "sources.json")).read_text())


class State:
    """What the collectors last saw. Readers get a consistent copy."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}
        self._updated = {}
        self.started = time.time()

    def put(self, key, value):
        with self._lock:
            self._data[key] = value
            self._updated[key] = time.time()

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def snapshot(self):
        with self._lock:
            data = json.loads(json.dumps(self._data))
            data["meta"] = {"started_at": self.started, "now": time.time(), "updated_at": dict(self._updated)}
            return data


@functools.lru_cache(maxsize=None)
def tls_context(ca_file=None, verify=True):
    # One context per distinct source, kept: building one for every request loads the whole CA bundle each time
    # and the process grew until its memory limit restarted it.
    if not verify:
        return ssl._create_unverified_context()  # noqa: S323 - only for sources marked "verify": false in sources.json
    return ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()


def fetch(url, headers=None, data=None, context=None, opener=None, timeout=TIMEOUT):
    """(status, body, milliseconds). A response with an error status is a result, not an exception."""
    request = urllib.request.Request(url, data=data, headers={"User-Agent": "homelab-metrics", **(headers or {})})
    started = time.monotonic()
    try:
        if opener is not None:
            response = opener.open(request, timeout=timeout)
        else:
            response = urllib.request.urlopen(request, timeout=timeout, context=context)  # noqa: S310 - URLs come from sources.json
        with response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    return status, body, round((time.monotonic() - started) * 1000)


def fetch_json(url, **kwargs):
    status, body, _ = fetch(url, **kwargs)
    if status != 200:
        raise RuntimeError(f"HTTP {status}")
    return json.loads(body)


def percent(used, total):
    return round(used / total * 100, 1) if total else 0.0


def error_name(error):
    reason = getattr(error, "reason", None)
    return type(reason).__name__ if isinstance(reason, Exception) else type(error).__name__


# ── Proxmox ─────────────────────────────────────────────────────────────────────────────────────────────────

def proxmox_get(cluster, path):
    """One GET on the first endpoint of the cluster that answers (any node serves the whole cluster)."""
    token = os.environ.get(cluster["token_env"], "")
    context = tls_context(cluster.get("ca_file") and str(HERE / cluster["ca_file"]), cluster.get("verify", True))
    last = None
    for endpoint in cluster["endpoints"]:
        try:
            return fetch_json(f"{endpoint}/api2/json{path}", headers={"Authorization": f"PVEAPIToken={token}"}, context=context)["data"]
        except (urllib.error.URLError, TimeoutError, ConnectionError, RuntimeError, ValueError) as error:
            last = error
    raise last


def empty_node(label, error=None):
    node = {"label": label, "online": False, "cpu_percent": 0.0, "cores": 0, "load1": 0.0, "uptime_seconds": 0,
            "ram_used_bytes": 0, "ram_total_bytes": 0, "ram_percent": 0.0,
            "storage_used_bytes": 0, "storage_total_bytes": 0, "storage_percent": 0.0,
            "vms_running": 0, "vms_total": 0, "lxc_running": 0, "lxc_total": 0}
    if error:
        node["error"] = error
    return node


def proxmox_nodes(cluster, resources, loads):
    """Per-node figures from /cluster/resources. Templates are not counted as guests; a node's storage is what
    it holds itself (shared storage is counted once, in the cluster total)."""
    nodes = {}
    for name, spec in cluster["nodes"].items():
        entry = next((r for r in resources if r["type"] == "node" and r["node"] == name), None)
        node = empty_node(spec["label"])
        if entry is None or entry.get("status") != "online":
            node["error"] = "not in the cluster" if entry is None else "offline"
            nodes[spec["key"]] = node
            continue
        guests = [r for r in resources if r["type"] in ("qemu", "lxc") and r.get("node") == name and not r.get("template")]
        local = [r for r in resources if r["type"] == "storage" and r.get("node") == name and not r.get("shared") and r.get("status") == "available"]
        used, total = sum(r.get("disk", 0) for r in local), sum(r.get("maxdisk", 0) for r in local)
        node.update({
            "online": True,
            "cpu_percent": round(entry.get("cpu", 0) * 100, 1), "cores": entry.get("maxcpu", 0),
            "load1": loads.get(name, 0.0), "uptime_seconds": entry.get("uptime", 0),
            "ram_used_bytes": entry.get("mem", 0), "ram_total_bytes": entry.get("maxmem", 0),
            "ram_percent": percent(entry.get("mem", 0), entry.get("maxmem", 0)),
            "storage_used_bytes": used, "storage_total_bytes": total, "storage_percent": percent(used, total),
            "vms_running": sum(1 for g in guests if g["type"] == "qemu" and g.get("status") == "running"),
            "vms_total": sum(1 for g in guests if g["type"] == "qemu"),
            "lxc_running": sum(1 for g in guests if g["type"] == "lxc" and g.get("status") == "running"),
            "lxc_total": sum(1 for g in guests if g["type"] == "lxc"),
        })
        nodes[spec["key"]] = node
    return nodes


def shared_storage(resources):
    """Shared storage appears once per node in /cluster/resources: count each name once."""
    seen = {}
    for r in resources:
        if r["type"] == "storage" and r.get("shared") and r.get("status") == "available":
            seen[r["storage"]] = (r.get("disk", 0), r.get("maxdisk", 0))
    return sum(v[0] for v in seen.values()), sum(v[1] for v in seen.values())


def guest_states(resources):
    return {str(r["vmid"]): {"status": r.get("status", "unknown"), "node": r.get("node"), "name": r.get("name")}
            for r in resources if r["type"] in ("qemu", "lxc")}


def collect_proxmox(state, sources):
    nodes, guests, summary_nodes, storage = {}, {}, [], [0, 0]
    for cluster in sources["proxmox"]:
        if not os.environ.get(cluster["token_env"]):
            for spec in cluster["nodes"].values():
                nodes[spec["key"]] = empty_node(spec["label"], "not connected yet")
            continue
        try:
            resources = proxmox_get(cluster, "/cluster/resources")
        except Exception as error:  # noqa: BLE001 - a failing cluster must not stop the others
            for spec in cluster["nodes"].values():
                nodes[spec["key"]] = empty_node(spec["label"], f"Proxmox: {error_name(error)}")
            continue
        loads = {}
        for name in cluster["nodes"]:
            try:
                loads[name] = float(proxmox_get(cluster, f"/nodes/{name}/status")["loadavg"][0])
            except Exception:  # noqa: BLE001, S110 - the load is a detail; the node figures still stand
                pass
        found = proxmox_nodes(cluster, resources, loads)
        nodes.update(found)
        guests[cluster["id"]] = guest_states(resources)
        if cluster.get("summary"):
            summary_nodes += [n for n in found.values() if n["online"]]
            shared = shared_storage(resources)
            storage[0] += shared[0] + sum(n["storage_used_bytes"] for n in found.values())
            storage[1] += shared[1] + sum(n["storage_total_bytes"] for n in found.values())
    cores = sum(n["cores"] for n in summary_nodes)
    ram_used, ram_total = sum(n["ram_used_bytes"] for n in summary_nodes), sum(n["ram_total_bytes"] for n in summary_nodes)
    state.put("nodes", nodes)
    state.put("guests", guests)
    state.put("summary", {
        "compute": {"cpu_percent": round(sum(n["cpu_percent"] * n["cores"] for n in summary_nodes) / cores, 1) if cores else 0.0,
                    "cpu_load": round(sum(n["load1"] for n in summary_nodes), 2), "cores": cores,
                    "ram_used_bytes": ram_used, "ram_free_bytes": ram_total - ram_used, "ram_total_bytes": ram_total,
                    "ram_percent": percent(ram_used, ram_total)},
        "storage": {"used_bytes": storage[0], "free_bytes": storage[1] - storage[0], "total_bytes": storage[1],
                    "percent": percent(storage[0], storage[1])},
    })
    state.put("remote", remote_machines(sources, guests))


def remote_machines(sources, guests):
    services = {}
    for name, machine in sources.get("remote", {}).items():
        guest = guests.get(machine["cluster"], {}).get(str(machine["vmid"]))
        status = guest["status"] if guest else "missing"
        services[machine["card"]] = {"name": name, "label": machine["label"], "vmid": machine["vmid"], "host": machine["host"],
                                     "status": status, "running": status == "running"}
    return {"services": services}


# ── Prometheus: k3s and PostgreSQL ──────────────────────────────────────────────────────────────────────────

def prom(base, expression):
    result = fetch_json(f"{base}/api/v1/query?" + urllib.parse.urlencode({"query": expression}))
    return result["data"]["result"]


def prom_number(base, expression):
    result = prom(base, expression)
    return float(result[0]["value"][1]) if result else 0.0


def collect_k3s(state, sources):
    base = sources["prometheus"]
    try:
        k3s = {
            "online": True,
            "nodes_ready": int(prom_number(base, 'sum(kube_node_status_condition{condition="Ready",status="true"})')),
            "nodes_total": int(prom_number(base, 'count(kube_node_status_condition{condition="Ready",status="true"})')),
            "pods_running": int(prom_number(base, 'sum(kube_pod_status_phase{phase="Running"})')),
            "pods_failing": int(prom_number(base, 'sum(kube_pod_status_phase{phase=~"Pending|Failed|Unknown"})')),
            "workloads_ready": int(prom_number(base, "count(kube_deployment_status_replicas_available >= kube_deployment_spec_replicas)")),
            "workloads_total": int(prom_number(base, "count(kube_deployment_spec_replicas)")),
            "restarts_day": int(prom_number(base, "sum(increase(kube_pod_container_status_restarts_total[24h]))")),
        }
    except Exception as error:  # noqa: BLE001
        k3s = {"online": False, "error": f"Prometheus: {error_name(error)}"}
    state.put("k3s", k3s)


def postgres_members(running, primary, written, replayed, versions):
    """Members of the Patroni cluster from its own metrics; a replica's lag is what the leader has written and
    the replica has not replayed yet."""
    leader_position = max([v for name, v in written.items() if primary.get(name)], default=0)
    members = []
    for name in sorted(running):
        is_leader = bool(primary.get(name))
        lag = None if is_leader else max(0, int(leader_position - replayed.get(name, 0)))
        members.append({"name": name, "role": "leader" if is_leader else "replica", "running": bool(running[name]), "lag_bytes": lag})
    version = next(iter(versions.values()), 0)
    return {
        "online": any(m["role"] == "leader" and m["running"] for m in members),
        "leader": next((m["name"] for m in members if m["role"] == "leader"), None),
        "members": members,
        "members_running": sum(1 for m in members if m["running"]), "members_total": len(members),
        "version": f"{int(version) // 10000}.{int(version) % 10000}" if version else None,
    }


def collect_postgres(state, sources):
    base = sources["prometheus"]

    def by_name(metric):
        return {r["metric"].get("name", r["metric"].get("instance")): float(r["value"][1]) for r in prom(base, metric)}

    try:
        postgres = postgres_members(by_name("patroni_postgres_running"), by_name("patroni_primary"), by_name("patroni_xlog_location"),
                                    by_name("patroni_xlog_replayed_location"), by_name("patroni_postgres_server_version"))
    except Exception as error:  # noqa: BLE001
        postgres = {"online": False, "error": f"Prometheus: {error_name(error)}", "members": []}
    state.put("postgres", postgres)


# ── HTTP checks ─────────────────────────────────────────────────────────────────────────────────────────────

def check_service(check):
    """Is the address answering, how fast, and (for the applications that say it without a login) which version."""
    context = tls_context(verify=check.get("verify", True))
    result = {"label": check["label"], "url": check["url"], "online": False}
    try:
        status, body, elapsed = fetch(check["url"], context=context)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
        result["error"] = error_name(error)
        return result
    result.update({"status_code": status, "response_ms": elapsed, "online": status < 500 and status not in (404,)})
    try:
        kind = check.get("kind")
        if kind == "forgejo" and status == 200:
            result["version"] = json.loads(body)["version"]
            base = check["url"].rsplit("/api/v1/", 1)[0]
            for key, path in (("public_orgs", "/api/v1/orgs?limit=1"), ("public_repos", "/api/v1/repos/search?limit=1")):
                request = urllib.request.Request(base + path, headers={"User-Agent": "homelab-metrics"})
                with urllib.request.urlopen(request, timeout=TIMEOUT, context=context) as response:  # noqa: S310
                    result[key] = int(response.headers.get("X-Total-Count", "0"))
        elif kind == "nextcloud" and status == 200:
            info = json.loads(body)
            result.update({"version": info.get("versionstring"), "maintenance": bool(info.get("maintenance")),
                           "needs_db_upgrade": bool(info.get("needsDbUpgrade"))})
        elif kind == "json-version" and status == 200:
            info = json.loads(body)
            result["version"] = str(info.get(check.get("field", "version"), "")) or None
        elif kind == "text-version" and status == 200:
            result["version"] = body.decode(errors="replace").strip()[:40]
    except (ValueError, KeyError, TypeError, urllib.error.URLError, TimeoutError, ConnectionError):
        pass  # the address answers; the detail is optional
    return result


def collect_services(state, sources):
    results = {}
    threads = []

    def run(key, check):
        results[key] = check_service(check)

    for key, check in sources["services"].items():
        thread = threading.Thread(target=run, args=(key, check), daemon=True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join(TIMEOUT * 3)
    state.put("services", results)


# ── The NAS, from the monitoring stack; then sources that need a credential of their own ─────────────────────────────────────────────────────────────

def truenas_snapshot(up, info, load, uptime, threads, memory, status, healthy, size, allocated, free, apps):
    """The NAS as the monitoring stack sees it (the two exporters of services/observability/truenas.yaml)."""
    if not up:
        return {"configured": True, "online": False, "error": "no metrics from the NAS", "disks": []}
    disks = [{"label": pool, "status": status.get(pool), "healthy": bool(healthy.get(pool)),
              "used_bytes": int(allocated.get(pool, 0)), "free_bytes": int(free.get(pool, 0)), "total_bytes": int(size.get(pool, 0)),
              "percent": percent(allocated.get(pool, 0), size.get(pool, 0))} for pool in sorted(healthy)]
    return {
        "configured": True, "online": True, "disks": disks, "healthy": all(d["healthy"] for d in disks),
        "apps": [{"id": name, "running": bool(value)} for name, value in sorted(apps.items())],
        "system": {"load1": load, "uptime_seconds": int(uptime), "cores": int(threads) or None,
                   "ram_total_bytes": int(memory) or None, "version": next(iter(info), None)},
    }


def collect_truenas(state, sources):
    """No call to the NAS: its figures are already in VictoriaMetrics, so the page needs no key of its own."""
    if not sources.get("truenas"):
        return
    base = sources["prometheus"]

    def by(label, expression):
        return {r["metric"].get(label): float(r["value"][1]) for r in prom(base, expression)}

    try:
        truenas = truenas_snapshot(
            prom_number(base, "max(truenas_exporter_up)"), by("version", "truenas_info"), prom_number(base, 'truenas_load{minutes="1"}'),
            prom_number(base, "truenas_uptime_seconds"), prom_number(base, 'count(truenas_cpu_usage_percent{cpu!=""})'),
            prom_number(base, 'truenas_memory_bytes{kind="total"}'), {r["metric"].get("pool"): r["metric"].get("status") for r in prom(base, "truenas_pool_status")},
            by("pool", "truenas_pool_healthy"), by("pool", "truenas_pool_size_bytes"), by("pool", "truenas_pool_allocated_bytes"),
            by("pool", "truenas_pool_free_bytes"), by("app", "truenas_app_running"))
    except Exception as error:  # noqa: BLE001
        truenas = {"configured": True, "online": False, "error": f"Prometheus: {error_name(error)}", "disks": []}
    state.put("truenas", truenas)


def plex_sessions(container):
    sessions = []
    for item in container.get("Metadata", []):
        duration, offset = int(item.get("duration") or 0), int(item.get("viewOffset") or 0)
        subtitle = item.get("grandparentTitle")
        if subtitle and item.get("parentIndex") is not None and item.get("index") is not None:
            subtitle += f" · S{item['parentIndex']}E{item['index']}"
        sessions.append({"title": item.get("title"), "subtitle": subtitle, "user": (item.get("User") or {}).get("title"),
                         "player": (item.get("Player") or {}).get("title") or (item.get("Player") or {}).get("product"),
                         "state": (item.get("Player") or {}).get("state"), "elapsed_ms": offset, "duration_ms": duration,
                         "percent": percent(offset, duration)})
    return sessions


def collect_plex(state, sources):
    spec, token = sources.get("plex"), os.environ.get("PLEX_TOKEN")
    if not spec:
        return
    if not token:
        state.put("plex", {"configured": False})
        return
    headers = {"X-Plex-Token": token, "Accept": "application/json"}
    try:
        container = fetch_json(f"{spec['url']}/status/sessions", headers=headers)["MediaContainer"]
        previous = state.get("plex") or {}
        library = previous.get("library") if time.time() - previous.get("library_at", 0) < 600 else None
        library_at = previous.get("library_at", 0)
        if library is None:
            library, library_at = {"movies": 0, "shows": 0}, time.time()
            for section in fetch_json(f"{spec['url']}/library/sections", headers=headers)["MediaContainer"].get("Directory", []):
                if section.get("type") not in ("movie", "show"):
                    continue
                size_url = f"{spec['url']}/library/sections/{section['key']}/all?X-Plex-Container-Start=0&X-Plex-Container-Size=0"
                total = fetch_json(size_url, headers=headers)["MediaContainer"].get("totalSize", 0)
                library["movies" if section["type"] == "movie" else "shows"] += int(total)
        sessions = plex_sessions(container)
        state.put("plex", {"configured": True, "online": True, "count": len(sessions), "sessions": sessions,
                           "library": library, "library_at": library_at})
    except Exception as error:  # noqa: BLE001
        state.put("plex", {"configured": True, "online": False, "error": error_name(error), "sessions": []})


class Qbit:
    """qBittorrent needs a session cookie; the transfer speeds are kept as a short series for the chart."""

    def __init__(self):
        self.opener = None
        self.series = []

    def login(self, spec):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        data = urllib.parse.urlencode({"username": os.environ["QBIT_USERNAME"], "password": os.environ["QBIT_PASSWORD"]}).encode()
        status, body, _ = fetch(f"{spec['url']}/api/v2/auth/login", headers={"Referer": spec["url"]}, data=data, opener=opener)
        if status != 200 or body.strip() != b"Ok.":
            raise RuntimeError("login refused")
        self.opener = opener

    def collect(self, state, sources):
        spec = sources.get("qbit")
        if not spec:
            return
        if not (os.environ.get("QBIT_USERNAME") and os.environ.get("QBIT_PASSWORD")):
            state.put("qbit", {"configured": False})
            return
        try:
            if self.opener is None:
                self.login(spec)
            status, body, _ = fetch(f"{spec['url']}/api/v2/transfer/info", opener=self.opener)
            if status == 403:
                self.login(spec)
                status, body, _ = fetch(f"{spec['url']}/api/v2/transfer/info", opener=self.opener)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            info = json.loads(body)
            status, body, _ = fetch(f"{spec['url']}/api/v2/torrents/info", opener=self.opener)
            torrents = json.loads(body) if status == 200 else []
            leeching = ("downloading", "stalledDL", "metaDL", "forcedDL", "queuedDL", "checkingDL", "allocating")
            current = {"timestamp": int(time.time()), "download_bps": info.get("dl_info_speed", 0), "upload_bps": info.get("up_info_speed", 0),
                       "leech": sum(1 for t in torrents if t.get("state") in leeching),
                       "seed": sum(1 for t in torrents if t.get("state") in ("uploading", "stalledUP", "forcedUP", "queuedUP"))}
            self.series = (self.series + [{k: current[k] for k in ("timestamp", "download_bps", "upload_bps")}])[-SERIES_POINTS:]
            state.put("qbit", {"configured": True, "online": True, "current": current, "series": self.series})
        except Exception as error:  # noqa: BLE001
            self.opener = None
            state.put("qbit", {"configured": True, "online": False, "error": error_name(error), "series": self.series})


# ── Server ──────────────────────────────────────────────────────────────────────────────────────────────────

def rdp_file(machine):
    lines = [f"full address:s:{machine['host']}", "prompt for credentials:i:1", "administrative session:i:0",
             "screen mode id:i:2", "use multimon:i:0", "audiomode:i:0", "redirectclipboard:i:1"]
    return ("\r\n".join(lines) + "\r\n").encode()


def make_handler(state, sources):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type="application/json", extra=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (extra or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 - name required by http.server
            path = self.path.split("?", 1)[0]
            if path == "/health":
                snapshot = state.snapshot()
                self.reply(200, json.dumps({"status": "ok", "meta": snapshot["meta"]}).encode())
            elif path == "/api/snapshot":
                self.reply(200, json.dumps(state.snapshot()).encode())
            elif path.startswith("/api/rdp/"):
                machine = sources.get("remote", {}).get(path.rsplit("/", 1)[1])
                if machine is None:
                    self.reply(404, b'{"error": "unknown machine"}')
                else:
                    name = path.rsplit("/", 1)[1]
                    self.reply(200, rdp_file(machine), "application/x-rdp", {"Content-Disposition": f'attachment; filename="{name}.rdp"'})
            else:
                self.reply(404, b'{"error": "not found"}')

        def log_message(self, *_args):  # requests are not worth a log line each
            pass

    return Handler


def every(seconds, function, *args):
    def loop():
        while True:
            started = time.monotonic()
            try:
                function(*args)
            except Exception as error:  # noqa: BLE001 - a collector never takes the server down
                print(f"{function.__name__}: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
            time.sleep(max(1.0, seconds - (time.monotonic() - started)))

    threading.Thread(target=loop, daemon=True, name=function.__name__).start()


def main():
    sources, state, qbit = load_sources(), State(), Qbit()
    intervals = sources["intervals"]
    every(intervals["proxmox"], collect_proxmox, state, sources)
    every(intervals["k3s"], collect_k3s, state, sources)
    every(intervals["postgres"], collect_postgres, state, sources)
    every(intervals["services"], collect_services, state, sources)
    every(intervals["truenas"], collect_truenas, state, sources)
    every(intervals["plex"], collect_plex, state, sources)
    every(intervals["qbit"], qbit.collect, state, sources)
    port = int(os.environ.get("PORT", "9101"))
    print(f"homelab-metrics listening on :{port}", flush=True)
    ThreadingHTTPServer(("", port), make_handler(state, sources)).serve_forever()


if __name__ == "__main__":
    main()
