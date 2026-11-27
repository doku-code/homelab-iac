#!/usr/bin/env python3
"""Lean observability (TASK-020): render the pinned charts with our values and check the allow-lists, the
access rules and that every dashboard and alert query uses a metric that is actually collected.

Needs `helm` and the chart downloads; no cluster access.
"""
import json
import os
import re
import subprocess
import sys
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


def truenas(cluster, rules):
    """The NAS: its Graphite stream reduced to named metrics without serial numbers, its state read through the
    API with a key that is only a Secret, and every query of its dashboard and alerts answered by one of the two."""
    docs = list(yaml.safe_load_all((OBS / "truenas.yaml").read_text()))
    by = {(d["kind"], d["metadata"]["name"]): d for d in docs}
    assert all(d["metadata"]["namespace"] == "monitoring" for d in docs)
    assert all(d["spec"]["replicas"] == 1 for d in docs if d["kind"] == "Deployment"), "one replica per service"
    door = by["Service", "truenas-graphite-ingest"]["spec"]
    assert door["type"] == "LoadBalancer" and door["loadBalancerSourceRanges"] == ["192.168.0.13/32"], "only the NAS may push"
    for deployment in ("truenas-graphite", "truenas-exporter"):
        (container,) = by["Deployment", deployment]["spec"]["template"]["spec"]["containers"]
        assert re.search(r":v?\d+\.\d+", container["image"]) and "latest" not in container["image"], "pinned image"
        assert container["securityContext"]["readOnlyRootFilesystem"] and container["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    (exporter,) = by["Deployment", "truenas-exporter"]["spec"]["template"]["spec"]["containers"]
    env = {e["name"]: e for e in exporter["env"]}
    assert env["TRUENAS_API_KEY"]["valueFrom"]["secretKeyRef"] == {"name": "truenas-api", "key": "api-key"}, "the key is never in Git"
    assert env["TRUENAS_URL"]["value"].startswith("wss://"), "TrueNAS revokes a key sent without TLS"
    source = (OBS / "truenas-exporter.py").read_text()
    called = set(re.findall(r'session\.call\("([a-z_.]+)"', source))
    assert called == {"auth.login_with_api_key", "system.info", "pool.query", "pool.dataset.query", "disk.temperatures", "app.query", "alert.list"}, "read-only calls"
    mapping = yaml.safe_load((OBS / "truenas-mapping.yml").read_text())["mappings"]
    assert mapping[-1] == {"match": ".", "match_type": "regex", "action": "drop", "name": "dropped"}, "what is not named is dropped"
    assert not any("serial" in m["match"] for m in mapping), "disks by device name only"
    known = {m["name"] for m in mapping[:-1]} | set(re.findall(r'metric\("(truenas_[a-z_]+)"', source)) | {"truenas_exporter_up"}
    dashboard = json.loads((OBS / "dashboards/truenas.json").read_text())
    queries = [t["expr"] for panel in dashboard["panels"] for t in panel.get("targets", [])]
    own = [rule for rule in rules if rule["alert"].startswith("TrueNAS")]
    assert len(own) == 7 and len(queries) >= 15
    used = {name for query in queries + [rule["expr"] for rule in own] for name in re.findall(r"\btruenas_[a-z0-9_]+", query)}
    assert used <= known, sorted(used - known)
    assert all('job="truenas"' in query for query in queries + [rule["expr"] for rule in own])
    assert cluster.count('"instance" = "truenas"') == 2 and "truenas-graphite.monitoring.svc:9108" in cluster and "truenas-exporter.monitoring.svc:9110" in cluster
    generator = {g["name"]: g["files"] for g in yaml.safe_load((OBS / "kustomization.yaml").read_text())["configMapGenerator"]}
    assert generator["truenas-graphite-mapping"] == ["truenas-mapping.yml"] and generator["truenas-exporter"] == ["truenas-exporter.py"]
    assert "dashboards/truenas.json" in generator["grafana-dashboards"]


def main():
    # VictoriaMetrics: storage and queries only, one StatefulSet that scrapes nothing; 90 days.
    docs, text = render("victoria-metrics", "victoria-metrics-single", "OBS_VM_REPO", "OBS_VM_CHART", "victoriametrics.yaml")
    assert [d["kind"] for d in docs].count("StatefulSet") == 1 and not any(d["kind"] in ("Deployment", "DaemonSet", "ConfigMap") for d in docs)
    assert "promscrape" not in text, "Alloy collects; VictoriaMetrics scrapes nothing"
    for flag in ("--retentionPeriod=90d", "--search.maxStalenessInterval=5m", "--httpListenAddr=:8428", "storageClassName: local-path"):
        assert flag in text, flag
    assert next(d for d in docs if d["kind"] == "Service")["metadata"]["name"] == "victoria-metrics"
    # vmalert: the rules, evaluated once a minute, their state written back; firing alerts go to Alertmanager,
    # which posts to Discord with a webhook read from a mounted Secret, never from Git.
    docs, text = render("vmalert", "victoria-metrics-alert", "OBS_VM_REPO", "OBS_VMALERT_CHART", "vmalert.yaml")
    assert "--notifier.url=http://alertmanager.monitoring.svc" in text and "--evaluationInterval=1m" in text
    alerting = yaml.safe_load((OBS / "vmalert.yaml").read_text())["alertmanager"]
    (receiver,) = alerting["config"]["receivers"]
    assert alerting["config"]["route"]["receiver"] == receiver["name"] == "discord"
    assert receiver["discord_configs"] == [{"webhook_url_file": "/etc/alertmanager-discord/url", "send_resolved": True}]
    assert "discord.com" not in text and "webhook_url:" not in text, "the webhook address is not in Git"
    assert alerting["extraVolumes"] == [{"name": "discord", "secret": {"secretName": "alertmanager-discord"}}]
    assert "alertmanager-discord" in MAKEFILE and "DISCORD_ALERT_WEBHOOK" in MAKEFILE
    for flag in ("datasource", "remoteWrite", "remoteRead"):
        assert f"--{flag}.url=http://victoria-metrics.monitoring.svc:8428" in text, flag
    config = next(d for d in docs if d["kind"] == "ConfigMap" and "alert-rules.yaml" in d["data"])["data"]
    rules = [rule for group in yaml.safe_load(config["alert-rules.yaml"])["groups"] for rule in group["rules"]]
    assert len(rules) >= 8 and all(r["labels"]["severity"] in ("warning", "critical") and r["annotations"]["summary"] and r["for"] for r in rules)
    assert not any("timestamp(" in r["expr"] for r in rules), "a silent host is found with lag(): timestamp() never exceeds the staleness interval"
    # kube-state-metrics: only the allow-list.
    docs, text = render("kube-state-metrics", "kube-state-metrics", "OBS_PROMETHEUS_REPO", "OBS_KSM_CHART", "kube-state-metrics.yaml")
    values = yaml.safe_load((OBS / "kube-state-metrics.yaml").read_text())
    ksm_allowed = set(values["metricAllowlist"])
    assert "--metric-allowlist=" + ",".join(values["metricAllowlist"]) in text
    assert next(d for d in docs if d["kind"] == "Service")["metadata"]["name"] == "kube-state-metrics"

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
    assert "/proxy/" not in cluster and len(keep_regexes(cluster)) == 3
    truenas(cluster, rules)
    assert set(re.findall(r'scrape_interval\s*=\s*"(\w+)"', cluster)) == {"60s", "15s"}, "the switch is read more often: its byte counters are 32-bit"
    # The switch: asked over SNMPv3 for the columns it has; the sign-in is a mounted Secret, never in Git.
    snmp = yaml.safe_load((OBS / "snmp.yml").read_text())
    module = snmp["modules"]["qsw_if"]
    assert set(snmp) == {"modules"} and "auths" not in (OBS / "snmp.yml").read_text().replace("# ", ""), "no sign-in in Git"
    assert all(oid.startswith("1.3.6.1.2.1.2.2.1.") for oid in module["walk"]) and module["get"] == ["1.3.6.1.2.1.1.3.0"]
    assert "1.3.6.1.2.1.2.2.1.2" not in module["walk"], "the port descriptions are not asked: the switch does not answer 25 at once"
    assert {m["oid"] for m in module["metrics"]} - {"1.3.6.1.2.1.1.3"} == set(module["walk"])
    switch_metrics = {m["name"] for m in module["metrics"]}
    switch_keep = keep_regexes(cluster)[2]
    assert all(re.fullmatch(switch_keep, name) for name in switch_metrics), "everything the module reads is kept"
    assert 'config_files = ["/etc/alloy/snmp.yml", "/etc/alloy-snmp/auth.yml"]' in cluster and 'auth    = "switch_v3"' in cluster
    pod = next(d for d in docs if d["kind"] == "Deployment")["spec"]["template"]["spec"]
    assert {"name": "switch-snmp", "secret": {"secretName": "switch-snmp"}} in pod["volumes"]
    assert any(m["mountPath"] == "/etc/alloy-snmp" and m["readOnly"] for c in pod["containers"] for m in c.get("volumeMounts", []))
    generator = yaml.safe_load((OBS / "kustomization.yaml").read_text())["configMapGenerator"]
    assert "snmp.yml" in generator[0]["files"] and "dashboards/switch.json" in generator[1]["files"]
    auth_env = {"SWITCH_SNMP_USERNAME": "synthetic", "SWITCH_SNMP_AUTH_PASSWORD": "synthetic-auth: \"x\"", "SWITCH_SNMP_PRIVACY_PASSWORD": "synthetic-priv"}
    made = subprocess.run([sys.executable, str(ROOT / "scripts/switch-snmp-auth.py")], capture_output=True, text=True, env=auth_env)
    auth = yaml.safe_load(made.stdout)["auths"]["switch_v3"]
    assert (auth["version"], auth["security_level"], auth["auth_protocol"], auth["priv_protocol"]) == (3, "authPriv", "SHA", "DES")
    assert auth["password"] == auth_env["SWITCH_SNMP_AUTH_PASSWORD"] and auth["priv_password"] == "synthetic-priv"
    assert subprocess.run([sys.executable, str(ROOT / "scripts/switch-snmp-auth.py")], capture_output=True, env={}).returncode != 0
    assert "http://victoria-metrics.monitoring.svc:8428/api/v1/write" in cluster and "kube-state-metrics.monitoring.svc:8080" in cluster and "loki.source.kubernetes" in cluster

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
    assert ingest["routes"][0]["services"] == [{"name": "victoria-metrics", "port": 8428}]
    assert all([m["name"] for m in route["middlewares"]] == ["managed-vms"] for route in ingest["routes"])
    assert {route["match"].split(" && ")[1] for route in ingest["routes"]} == {"Path(`/api/v1/write`)", "Path(`/loki/api/v1/push`)"}
    assert [m["name"] for m in access[("IngressRoute", "grafana")]["spec"]["routes"][0]["middlewares"]] == ["admin-lan"]
    assert not any(kind == "Secret" for kind, _ in access), "no secret values in Git"

    # Agent on the VMs: pinned package and key, short collector list, PostgreSQL part only on the members.
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert re.fullmatch(r"\d+\.\d+\.\d+-\d+", defaults["alloy_agent_version"]) and re.fullmatch(r"[0-9a-f]{64}", defaults["alloy_agent_apt_signing_sha256"])
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
    # The switch dashboard and the network alerts only ask for what the SNMP module reads.
    switch = json.loads((OBS / "dashboards/switch.json").read_text())
    asked = [t["expr"] for panel in switch["panels"] for t in panel.get("targets", [])] + [r["expr"] for r in rules if "switch" in r["expr"]]
    named = {name for query in asked for name in re.findall(r"\b(?:if[A-Z][A-Za-z]+|sysUpTime)\b", query)} - {"ifIndex"}
    assert len(named) >= 8 and named <= switch_metrics, sorted(named - switch_metrics)
    assert all('job="switch"' in query for query in asked) and len([r for r in rules if "switch" in r["expr"]]) == 4
    assert all(panel["datasource"]["uid"] == "prometheus" for panel in switch["panels"] if panel["type"] != "row")

    for target, variable in (("observability-deploy", "OBSERVABILITY_DEPLOY_APPROVED"), ("observability-agents", "OBSERVABILITY_AGENTS_APPROVED")):
        result = subprocess.run(["make", "--no-print-directory", target], cwd=ROOT, capture_output=True, text=True,
                                env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        assert result.returncode != 0 and variable in result.stderr, target
    print("PASS: pinned charts, VictoriaMetrics scrapes nothing, allow-lists cover every dashboard and alert query, "
          "least-privilege collector, Grafana state in PostgreSQL, restricted routes, agent templates")


if __name__ == "__main__":
    main()
