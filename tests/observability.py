#!/usr/bin/env python3
"""Lean observability (TASK-020): render the pinned charts with our values and check the allow-lists, the
access rules and that every dashboard and alert query uses a metric that is actually collected.

Needs `helm` and the chart downloads; no cluster access.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "services/observability"
ROLE = ROOT / "ansible/roles/alloy_agent"
MAKEFILE = (ROOT / "Makefile").read_text()


def make_var(name):
    match = re.search(rf"^{name} := (.+)$", MAKEFILE, re.M)
    assert match, name
    return match.group(1).strip()


def render(release, chart, repo_var, version_var, values):
    version = make_var(version_var)
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{chart} chart is pinned"
    result = subprocess.run(["helm", "template", release, chart, "--repo", make_var(repo_var), "--version", version,
                             "--namespace", "monitoring", "-f", str(OBS / values)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return [d for d in yaml.safe_load_all(result.stdout) if d], result.stdout


def render_agent(host):
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        (base / "inventory.json").write_text(json.dumps({"all": {"vars": {**defaults, "ansible_connection": "local"}, "children": {
            "postgresql": {"hosts": {"pg-01": {"ansible_host": "192.168.0.61"}}},
            "storage": {"hosts": {"storage-01": {"ansible_host": "192.168.0.50"}}}}}}))
        (base / "render.yml").write_text(yaml.safe_dump([{"hosts": host, "gather_facts": False, "tasks": [
            {"ansible.builtin.template": {"src": str(ROLE / "templates/config.alloy.j2"), "dest": str(base / "out")}}]}]))
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", str(base / "inventory.json"), str(base / "render.yml")],
                                capture_output=True, text=True, env={**os.environ, "ANSIBLE_NOCOLOR": "1"})
        assert result.returncode == 0, result.stdout + result.stderr
        return (base / "out").read_text()


def keep_regexes(text):
    return [m.group(1) for m in re.finditer(r'regex\s*=\s*"([^"]+)"\s*\n\s*action\s*=\s*"keep"', text)]


def main():
    # Prometheus: storage and rules only; the chart's discovery jobs, Alertmanager and node exporter are off.
    docs, text = render("prometheus", "prometheus", "OBS_PROMETHEUS_REPO", "OBS_PROMETHEUS_CHART", "prometheus.yaml")
    assert not any(d["kind"] == "DaemonSet" for d in docs) and "alertmanager" not in text and "pushgateway" not in text
    config = next(d for d in docs if d["kind"] == "ConfigMap" and "prometheus.yml" in d["data"])["data"]
    scrape = yaml.safe_load(config["prometheus.yml"])
    assert [job["job_name"] for job in scrape["scrape_configs"]] == ["prometheus"], "Alloy collects; Prometheus scrapes only itself"
    assert scrape["scrape_configs"][0]["metric_relabel_configs"][0]["action"] == "keep"
    assert scrape["global"]["scrape_interval"] == "1m"
    for flag in ("--web.enable-remote-write-receiver", "--storage.tsdb.retention.time=15d", "--storage.tsdb.retention.size=8GB"):
        assert flag in text, flag
    values = yaml.safe_load((OBS / "prometheus.yaml").read_text())
    ksm_allowed = set(values["kube-state-metrics"]["metricAllowlist"])
    assert "--metric-allowlist=" + ",".join(values["kube-state-metrics"]["metricAllowlist"]) in text
    rules = [rule for group in yaml.safe_load(config["alerting_rules.yml"])["groups"] for rule in group["rules"]]
    assert len(rules) >= 8 and all(r["labels"]["severity"] in ("warning", "critical") and r["annotations"]["summary"] and r["for"] for r in rules)

    # Loki: one process, no caches, canary or gateway; seven days.
    docs, text = render("loki", "loki", "OBS_GRAFANA_LABS_REPO", "OBS_LOKI_CHART", "loki.yaml")
    assert [d["kind"] for d in docs].count("StatefulSet") == 1 and not any(d["kind"] in ("Deployment", "DaemonSet") for d in docs)
    assert "memcached" not in text and "canary" not in text and "retention_period: 168h" in text

    # Alloy in the cluster: one Deployment, no host access, least-privilege rules.
    docs, text = render("alloy", "alloy", "OBS_GRAFANA_LABS_REPO", "OBS_ALLOY_CHART", "alloy.yaml")
    assert [d["kind"] for d in docs].count("Deployment") == 1 and "hostPath" not in text
    role_rules = [rule for d in docs if d["kind"] == "ClusterRole" for rule in d["rules"]]
    granted = {r for rule in role_rules for r in rule.get("resources", [])}
    # nodes/pods (read-only pod list of a kubelet) is added by the chart itself.
    assert {"nodes/metrics", "pods/log"} <= granted <= {"nodes", "pods", "namespaces", "pods/log", "nodes/metrics", "nodes/pods"}, granted
    assert "nodes/proxy" not in granted and "secrets" not in granted
    assert {u for rule in role_rules for u in rule.get("nonResourceURLs", [])} <= {"/metrics"}
    assert all(set(rule["verbs"]) <= {"get", "list", "watch"} for rule in role_rules), "read-only"
    cluster = (OBS / "cluster.alloy").read_text()
    assert "/proxy/" not in cluster and len(keep_regexes(cluster)) == 2
    assert set(re.findall(r'scrape_interval\s*=\s*"(\w+)"', cluster)) == {"60s"}
    assert "http://prometheus-server.monitoring.svc/api/v1/write" in cluster and "loki.source.kubernetes" in cluster

    # Grafana: state in the shared PostgreSQL over TLS, passwords from Kubernetes Secrets, no volume.
    docs, text = render("grafana", "grafana", "OBS_GRAFANA_REPO", "OBS_GRAFANA_CHART", "grafana.yaml")
    assert not any(d["kind"] in ("PersistentVolumeClaim", "Ingress", "StatefulSet") for d in docs)
    grafana = yaml.safe_load((OBS / "grafana.yaml").read_text())
    database = grafana["grafana.ini"]["database"]
    assert (database["type"], database["host"], database["name"], database["ssl_mode"]) == ("postgres", "192.168.0.60:5432", "grafana", "require")
    assert "password" not in database and grafana["envValueFrom"]["GF_DATABASE_PASSWORD"]["secretKeyRef"]["name"] == "grafana-db"
    assert grafana["admin"]["existingSecret"] == "grafana-admin" and grafana["grafana.ini"]["users"]["allow_sign_up"] is False
    assert {d["uid"] for d in grafana["datasources"]["datasources.yaml"]["datasources"]} == {"prometheus", "loki"}
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert {"name": "grafana"} in apps

    # Routes: Grafana for the administration LAN; ingestion only for managed VMs and only the two write paths.
    access = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((OBS / "access.yaml").read_text())}
    assert access[("Middleware", "admin-lan")]["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24"]
    managed = access[("Middleware", "managed-vms")]["spec"]["ipAllowList"]["sourceRange"]
    assert "192.168.0.0/24" not in managed and "192.168.0.40/29" in managed
    ingest = access[("IngressRoute", "ingest")]["spec"]
    assert ingest["entryPoints"] == ["websecure"] and len(ingest["routes"]) == 2
    assert all([m["name"] for m in route["middlewares"]] == ["managed-vms"] for route in ingest["routes"])
    assert {route["match"].split(" && ")[1] for route in ingest["routes"]} == {"Path(`/api/v1/write`)", "Path(`/loki/api/v1/push`)"}
    assert [m["name"] for m in access[("IngressRoute", "grafana")]["spec"]["routes"][0]["middlewares"]] == ["admin-lan"]
    assert not any(kind == "Secret" for kind, _ in access), "no secret values in Git"

    # Agent on the VMs: pinned package and key, short collector list, PostgreSQL part only on the members.
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert re.fullmatch(r"\d+\.\d+\.\d+-\d+", defaults["alloy_agent_version"]) and re.fullmatch(r"[0-9a-f]{64}", defaults["alloy_agent_apt_key_sha256"])
    assert len(defaults["alloy_agent_collectors"]) <= 10 and "processes" not in defaults["alloy_agent_collectors"]
    plain, member = render_agent("storage-01"), render_agent("pg-01")
    assert "prometheus.exporter.postgres" not in plain and "patroni" not in plain
    assert 'replacement  = "storage-01"' in plain and "https://metrics.192.168.0.40.sslip.io/api/v1/write" in plain
    assert "host=/var/run/postgresql&user=alloy" in member and '"__address__" = "192.168.0.61:8008"' in member
    dsn = re.search(r'data_source_names = \["([^"]+)"\]', member).group(1)
    assert dsn.startswith("postgresql:///postgres?") and "password" not in dsn and "@" not in dsn, "local socket, no password"
    postgres_keep = keep_regexes(member)
    assert len(postgres_keep) == 1 and postgres_keep[0] == "|".join(defaults["alloy_agent_postgresql_metrics"])

    # Every metric a dashboard panel or an alert asks for is one we collect.
    kubelet_keep = keep_regexes(cluster)
    dashboard = json.loads((OBS / "dashboards/homelab-overview.json").read_text())
    queries = [t["expr"] for panel in dashboard["panels"] for t in panel.get("targets", []) if t["datasource"]["type"] == "prometheus"]
    queries += [rule["expr"] for rule in rules]
    used = {name for query in queries for name in re.findall(r"\b(?:node|pg|patroni|kube|kubelet|container)_[a-z0-9_]+", query)}
    assert len(used) >= 15, sorted(used)
    for name in sorted(used):
        if name.startswith(("node_", "patroni_")):
            continue  # host collectors and Patroni are not filtered by name
        if name.startswith("pg_"):
            assert re.fullmatch(postgres_keep[0], name), f"{name} is dropped by the PostgreSQL allow-list"
        elif name.startswith("kube_"):
            assert name in ksm_allowed, f"{name} is not in the kube-state-metrics allow-list"
        else:
            assert any(re.fullmatch(regex, name) for regex in kubelet_keep), f"{name} is dropped by the kubelet allow-lists"
    assert all(panel["datasource"]["uid"] in ("prometheus", "loki") for panel in dashboard["panels"] if panel["type"] != "row")

    for target, variable in (("observability-deploy", "OBSERVABILITY_DEPLOY_APPROVED"), ("observability-agents", "OBSERVABILITY_AGENTS_APPROVED")):
        result = subprocess.run(["make", "--no-print-directory", target], cwd=ROOT, capture_output=True, text=True,
                                env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        assert result.returncode != 0 and variable in result.stderr, target
    print("PASS: pinned charts, Prometheus scrapes only itself, allow-lists cover every dashboard and alert query, "
          "least-privilege collector, Grafana state in PostgreSQL, restricted routes, agent templates")


if __name__ == "__main__":
    main()
