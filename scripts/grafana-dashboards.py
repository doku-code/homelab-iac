#!/usr/bin/env python3
"""Writes the per-platform Grafana dashboards of services/observability/dashboards from the short descriptions
below, so that a panel is one line to add. The JSON files are committed; Argo CD hands them to Grafana.

  scripts/grafana-dashboards.py          rewrite the files
  scripts/grafana-dashboards.py --check  fail when a file differs from what this script writes (tests)

Hand-made dashboards (homelab-overview, switch, truenas, proxmox-hosts) are not touched.
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "services/observability/dashboards"
DS = {"type": "prometheus", "uid": "prometheus"}
GOOD_BAD = [("red", None), ("green", 1)]
BAD_GOOD = [("green", None), ("red", 1)]


class Board:
    def __init__(self, uid, title, tags, variables=()):
        self.uid, self.title, self.tags, self.variables = uid, title, tags, variables
        self.panels, self.y, self.x, self.row_height = [], 0, 0, 0

    def _place(self, w, h):
        if self.x + w > 24:
            self.x, self.y = 0, self.y + self.row_height
            self.row_height = 0
        position = {"h": h, "w": w, "x": self.x, "y": self.y}
        self.x, self.row_height = self.x + w, max(self.row_height, h)
        return position

    def row(self, title):
        self.y, self.x, self.row_height = self.y + self.row_height, 0, 0
        self.panels.append({"id": len(self.panels) + 1, "type": "row", "title": title, "collapsed": False, "panels": [],
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}})
        self.y += 1

    def stat(self, title, expr, unit="none", steps=None, w=4, legend="", description="", text="auto"):
        self.panels.append({
            "id": len(self.panels) + 1, "type": "stat", "title": title, "datasource": DS, "gridPos": self._place(w, 4), "description": description,
            "targets": [{"refId": "A", "expr": expr, "datasource": DS, "legendFormat": legend, "instant": True}],
            "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "thresholds"}, "thresholds": {
                "mode": "absolute", "steps": [{"color": c, "value": v} for c, v in (steps or [("green", None)])]}}, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none", "textMode": text}})

    def graph(self, title, targets, unit="short", w=12, h=8, description="", maximum=None, stack=False):
        defaults = {"unit": unit, "custom": {"lineWidth": 1, "fillOpacity": 25 if stack else 8, "showPoints": "never",
                                             "stacking": {"mode": "normal" if stack else "none"}}}
        if maximum is not None:
            defaults.update({"min": 0, "max": maximum})
        self.panels.append({
            "id": len(self.panels) + 1, "type": "timeseries", "title": title, "datasource": DS, "gridPos": self._place(w, h), "description": description,
            "targets": [{"refId": chr(65 + i), "expr": expr, "datasource": DS, "legendFormat": legend} for i, (expr, legend) in enumerate(targets)],
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "max"]}, "tooltip": {"mode": "multi", "sort": "desc"}}})

    def table(self, title, expr, unit="none", w=24, h=8, description="", steps=None):
        self.panels.append({
            "id": len(self.panels) + 1, "type": "table", "title": title, "datasource": DS, "gridPos": self._place(w, h), "description": description,
            "targets": [{"refId": "A", "expr": expr, "datasource": DS, "instant": True, "format": "table"}],
            "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": True, "__name__": True, "cluster": True, "instance": True}}}],
            "fieldConfig": {"defaults": {"unit": unit, "custom": {"cellOptions": {"type": "color-text"}}, "thresholds": {
                "mode": "absolute", "steps": [{"color": c, "value": v} for c, v in (steps or [("text", None)])]}}, "overrides": []},
            "options": {"showHeader": True, "sortBy": [{"displayName": "Value", "desc": False}]}})

    def json(self):
        variables = [{"name": name, "label": label, "type": "query", "datasource": DS, "query": {"query": query, "refId": name}, "definition": query,
                      "refresh": 2, "includeAll": True, "multi": True, "allValue": ".+", "current": {"selected": True, "text": "All", "value": "$__all"}, "sort": 1}
                     for name, label, query in self.variables]
        return {"uid": self.uid, "title": self.title, "tags": list(self.tags), "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
                "refresh": "1m", "time": {"from": "now-6h", "to": "now"}, "annotations": {"list": []}, "links": [],
                "templating": {"list": variables}, "panels": self.panels}


def probe(name):
    return f'{{job="integrations/blackbox/{name}"}}'


def pfsense():
    b = Board("pfsense", "pfSense and Internet", ["network", "pfsense"])
    wan, lan, job = 'device="re0"', 'device="igc0"', 'job="pfsense"'
    b.row("Is the Internet fine right now")
    b.stat("Time to reach the Internet", f"max(probe_duration_seconds{{job=~\"integrations/blackbox/internet-.+\"}})", "s", [("green", None), ("yellow", 0.15), ("red", 0.5)],
           description="A TCP connection to two public servers, every 15 s. Above half a second, pages feel slow and calls break up: the line is saturated or the provider has trouble.")
    b.stat("Internet reachable", "min(probe_success{job=~\"integrations/blackbox/internet-.+\"})", steps=GOOD_BAD, text="value")
    b.stat("LAN DNS lookup", f"probe_duration_seconds{probe('dns-shared-address')}", "s", [("green", None), ("yellow", 0.1), ("red", 1)],
           description="A lookup on 192.168.0.20, the address every device asks.")
    b.stat("DNS servers answering", "sum(probe_success{job=~\"integrations/blackbox/dns-0.\"})", steps=[("red", None), ("yellow", 1), ("green", 2)],
           description="dns-01 and dns-02 share the address 192.168.0.20; one is enough.")
    b.stat("Upload now", f"rate(node_network_transmit_bytes_total{{{job},{wan}}}[2m]) * 8", "bps", [("green", None), ("yellow", 40e6), ("red", 45e6)],
           description="The line is 400/50 Mbit/s. pfSense limits the upload to 46 Mbit/s so that the queue forms where it can be sorted (FQ-CoDel).")
    b.stat("Download now", f"rate(node_network_receive_bytes_total{{{job},{wan}}}[2m]) * 8", "bps")
    b.row("Latency")
    b.graph("Time to reach the Internet and pfSense", [("probe_duration_seconds{job=~\"integrations/blackbox/(internet-.+|gateway-pfsense)\"}", "{{job}}")], "s", w=16,
            description="When the Internet lines rise and the pfSense line stays flat, the trouble is on the line, not in the house.")
    b.graph("DNS lookups", [("probe_duration_seconds{job=~\"integrations/blackbox/dns-.+\"}", "{{job}}")], "s", w=8)
    b.row("The line (WAN)")
    b.graph("Upload and download", [(f"rate(node_network_transmit_bytes_total{{{job},{wan}}}[2m]) * 8", "upload"),
                                    (f"rate(node_network_receive_bytes_total{{{job},{wan}}}[2m]) * 8", "download")], "bps", w=16)
    b.graph("Errors and drops on the WAN port", [(f"rate(node_network_receive_errs_total{{{job},{wan}}}[5m]) + rate(node_network_transmit_errs_total{{{job},{wan}}}[5m])", "errors"),
                                                 (f"rate(node_network_receive_drop_total{{{job},{wan}}}[5m]) + rate(node_network_transmit_drop_total{{{job},{wan}}}[5m])", "drops")], "pps", w=8)
    b.row("pfSense itself")
    b.graph("Processor in use", [(f'100 * (1 - avg(rate(node_cpu_seconds_total{{{job},mode="idle"}}[5m])))', "pfSense")], "percent", w=8, maximum=100)
    b.graph("Load average", [(f"node_load1{{{job}}}", "1 min"), (f"node_load5{{{job}}}", "5 min")], w=8)
    b.graph("LAN port", [(f"rate(node_network_transmit_bytes_total{{{job},{lan}}}[2m]) * 8", "to the LAN"),
                         (f"rate(node_network_receive_bytes_total{{{job},{lan}}}[2m]) * 8", "from the LAN")], "bps", w=8)
    return b


def postgresql():
    b = Board("postgresql", "PostgreSQL", ["postgresql", "patroni"])
    b.row("Cluster")
    b.stat("Members running", "sum(patroni_postgres_running)", steps=[("red", None), ("yellow", 2), ("green", 3)])
    b.stat("Leader", "patroni_primary == 1", legend="{{name}}", text="name", steps=[("green", None)])
    b.stat("Standbys streaming", "sum(patroni_postgres_streaming)", steps=[("red", None), ("yellow", 1), ("green", 2)])
    b.stat("Version", "max(patroni_postgres_server_version)", description="180007 reads 18.7.")
    b.stat("Connections in use", "100 * sum(pg_stat_database_numbackends * on(instance) group_left() (patroni_primary == 1)) / max(pg_settings_max_connections)", "percent",
           [("green", None), ("yellow", 70), ("red", 90)])
    b.stat("Longest open transaction", "max(pg_stat_activity_max_tx_duration)", "s", [("green", None), ("yellow", 300), ("red", 3600)])
    b.row("Replication")
    b.graph("How far each standby is behind", [("clamp_min(scalar(max(patroni_xlog_location and on(name) (patroni_primary == 1))) - (patroni_xlog_replayed_location and on(name) (patroni_primary == 0)), 0)", "{{name}}")], "bytes",
            description="Bytes the leader has written and the standby has not replayed yet.")
    b.graph("Timeline", [("patroni_postgres_timeline", "{{name}}")], description="A step up is a failover or a promotion.")
    b.row("Activity, on the leader")
    leader = "* on(instance) group_left() (patroni_primary == 1)"
    b.graph("Connections per database", [(f"pg_stat_database_numbackends{{datname!~\"template.*|\"}} {leader}", "{{datname}}")], stack=True)
    b.graph("Transactions per second", [(f"rate(pg_stat_database_xact_commit{{datname!~\"template.*|\"}}[5m]) {leader}", "{{datname}}")], "ops", stack=True)
    b.graph("Rollbacks and deadlocks", [(f"rate(pg_stat_database_xact_rollback{{datname!~\"template.*|\"}}[5m]) {leader} > 0", "{{datname}} rollbacks/s"),
                                        (f"increase(pg_stat_database_deadlocks[1h]) {leader} > 0", "{{datname}} deadlocks in 1 h")])
    b.graph("Reads answered from memory", [(f"100 * rate(pg_stat_database_blks_hit{{datname!~\"template.*|\"}}[10m]) / (rate(pg_stat_database_blks_hit{{datname!~\"template.*|\"}}[10m]) + rate(pg_stat_database_blks_read{{datname!~\"template.*|\"}}[10m]) > 0) {leader}", "{{datname}}")],
            "percent", maximum=100, description="Share of block reads found in PostgreSQL's cache. Low for long means the memory is too small for that database.")
    b.row("Size")
    b.graph("Size per database", [(f"pg_database_size_bytes{{datname!~\"template.*\"}} {leader}", "{{datname}}")], "bytes", w=16, stack=True)
    b.graph("Data disk in use", [('100 * (1 - node_filesystem_avail_bytes{instance=~"pg-.+",mountpoint="/var/lib/postgresql"} / node_filesystem_size_bytes{instance=~"pg-.+",mountpoint="/var/lib/postgresql"})', "{{instance}}")],
            "percent", w=8, maximum=100)
    return b


def kubernetes():
    b = Board("kubernetes", "Kubernetes (k3s)", ["kubernetes", "k3s"], [("namespace", "Namespace", "label_values(kube_pod_info, namespace)")])
    ns = 'namespace=~"$namespace"'
    b.row("Cluster")
    b.stat("Nodes ready", 'sum(kube_node_status_condition{condition="Ready",status="true"})', steps=[("red", None), ("yellow", 2), ("green", 3)])
    b.stat("Pods running", f'sum(kube_pod_status_phase{{phase="Running",{ns}}})')
    b.stat("Pods not running", f'sum(kube_pod_status_phase{{phase=~"Pending|Failed|Unknown",{ns}}}) or vector(0)', steps=BAD_GOOD)
    b.stat("Deployments short of replicas", f"count(kube_deployment_status_replicas_available{{{ns}}} < kube_deployment_spec_replicas{{{ns}}}) or vector(0)", steps=BAD_GOOD)
    b.stat("Restarts in 24 h", f"sum(increase(kube_pod_container_status_restarts_total{{{ns}}}[24h]))", steps=[("green", None), ("yellow", 5), ("red", 20)])
    b.stat("Containers killed for memory, 24 h", f"sum(increase(container_oom_events_total{{{ns}}}[24h])) or vector(0)", steps=BAD_GOOD)
    b.row("What uses the cluster")
    b.graph("Processor per namespace", [(f'sum by (namespace) (rate(container_cpu_usage_seconds_total{{{ns}}}[5m]))', "{{namespace}}")], "cores", stack=True,
            description="Cores in use. The three nodes have their own dashboard (Virtual machines).")
    b.graph("Memory per namespace", [(f"sum by (namespace) (container_memory_working_set_bytes{{{ns}}})", "{{namespace}}")], "bytes", stack=True)
    b.graph("Processor, the ten busiest pods", [(f"topk(10, sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{{{ns}}}[5m])))", "{{namespace}}/{{pod}}")], "cores")
    b.graph("Memory, the ten largest pods", [(f"topk(10, sum by (namespace, pod) (container_memory_working_set_bytes{{{ns}}}))", "{{namespace}}/{{pod}}")], "bytes")
    b.row("Trouble")
    b.graph("Restarts per pod (per hour)", [(f"sum by (namespace, pod) (increase(kube_pod_container_status_restarts_total{{{ns}}}[1h])) > 0", "{{namespace}}/{{pod}}")])
    b.graph("Containers waiting, by reason", [(f"sum by (namespace, pod, reason) (kube_pod_container_status_waiting_reason{{{ns}}}) > 0", "{{namespace}}/{{pod}} {{reason}}")],
            description="ImagePullBackOff, CrashLoopBackOff and the like. Empty is good.")
    b.graph("Processor throttled", [(f"topk(10, sum by (namespace, pod) (rate(container_cpu_cfs_throttled_periods_total{{{ns}}}[5m])))", "{{namespace}}/{{pod}}")], "ops",
            description="Periods per second in which a container wanted more processor than its limit allows.")
    b.graph("Pods per node", [("kubelet_running_pods", "{{instance}}")])
    b.row("Volumes")
    b.graph("Volumes in use", [(f"100 * kubelet_volume_stats_used_bytes{{{ns}}} / kubelet_volume_stats_capacity_bytes{{{ns}}}", "{{namespace}}/{{persistentvolumeclaim}}")],
            "percent", w=16, maximum=100)
    b.stat("Volume claims not bound", f'sum(kube_persistentvolumeclaim_status_phase{{phase!="Bound",{ns}}}) or vector(0)', steps=BAD_GOOD, w=8)
    return b


def machines():
    b = Board("virtual-machines", "Virtual machines", ["vm", "hosts"], [("host", "Machine", 'label_values(node_uname_info{job="integrations/unix",instance!~"pve-.+"}, instance)')])
    host = 'job="integrations/unix",instance=~"$host",instance!~"pve-.+"'  # the Proxmox hosts have their own dashboard
    b.row("Now")
    b.stat("Machines reporting", f"count(node_uname_info{{{host}}})")
    b.stat("Fullest disk", f'max(100 * (1 - node_filesystem_avail_bytes{{{host},fstype!=""}} / node_filesystem_size_bytes{{{host},fstype!=""}}))', "percent",
           [("green", None), ("yellow", 80), ("red", 90)])
    b.stat("Highest memory use", f"max(100 * (1 - node_memory_MemAvailable_bytes{{{host}}} / node_memory_MemTotal_bytes{{{host}}}))", "percent", [("green", None), ("yellow", 85), ("red", 95)])
    b.stat("Highest processor use", f'max(100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{{{host},mode="idle"}}[5m]))))', "percent", [("green", None), ("yellow", 80), ("red", 95)])
    b.stat("Highest load (1 min)", f"max(node_load1{{{host}}})", steps=[("green", None), ("yellow", 4), ("red", 8)])
    b.stat("Read-only filesystems", f"sum(node_filesystem_readonly{{{host},fstype=~\"ext4|xfs|btrfs\"}}) or vector(0)", steps=BAD_GOOD)
    b.row("Processor and memory")
    b.graph("Processor in use", [(f'100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{{{host},mode="idle"}}[5m])))', "{{instance}}")], "percent", maximum=100)
    b.graph("Memory in use", [(f"100 * (1 - node_memory_MemAvailable_bytes{{{host}}} / node_memory_MemTotal_bytes{{{host}}})", "{{instance}}")], "percent", maximum=100)
    b.graph("Load average (1 min)", [(f"node_load1{{{host}}}", "{{instance}}")])
    b.graph("Processor time stolen by the host", [(f'100 * avg by (instance) (rate(node_cpu_seconds_total{{{host},mode="steal"}}[5m]))', "{{instance}}")], "percent",
            description="Time the VM wanted the processor and the Proxmox host gave it to another guest.")
    b.row("Disks")
    b.graph("Filesystems in use", [(f'100 * (1 - node_filesystem_avail_bytes{{{host},fstype!=""}} / node_filesystem_size_bytes{{{host},fstype!=""}})', "{{instance}} {{mountpoint}}")], "percent", maximum=100)
    b.graph("Time the disk was busy", [(f"100 * rate(node_disk_io_time_seconds_total{{{host}}}[5m])", "{{instance}} {{device}}")], "percent", maximum=100)
    b.graph("Read and written", [(f"sum by (instance) (rate(node_disk_read_bytes_total{{{host}}}[5m]))", "{{instance}} read"),
                                 (f"sum by (instance) (rate(node_disk_written_bytes_total{{{host}}}[5m]))", "{{instance}} written")], "Bps")
    b.graph("Time tasks waited for disk (pressure)", [(f"rate(node_pressure_io_waiting_seconds_total{{{host}}}[5m])", "{{instance}}")], "percentunit")
    b.row("Network")
    b.graph("Received", [(f"sum by (instance) (rate(node_network_receive_bytes_total{{{host}}}[5m])) * 8", "{{instance}}")], "bps")
    b.graph("Sent", [(f"sum by (instance) (rate(node_network_transmit_bytes_total{{{host}}}[5m])) * 8", "{{instance}}")], "bps")
    return b


def services():
    b = Board("service-health", "Service health", ["services", "probes"])
    web = 'instance="prometheus.exporter.blackbox.web"'
    b.row("Now")
    b.stat("Services answering", f"sum(probe_success{{{web}}})")
    b.stat("Services not answering", f"count(probe_success{{{web}}} == 0) or vector(0)", steps=BAD_GOOD)
    b.stat("Slowest answer", f"max(probe_duration_seconds{{{web}}})", "s", [("green", None), ("yellow", 2), ("red", 5)])
    b.stat("Availability, 24 h", f"100 * avg(avg_over_time(probe_success{{{web}}}[24h]))", "percent", [("red", None), ("yellow", 99), ("green", 99.9)], w=6)
    b.stat("Availability, 7 days", f"100 * avg(avg_over_time(probe_success{{{web}}}[7d]))", "percent", [("red", None), ("yellow", 99), ("green", 99.9)], w=6)
    b.row("Each service")
    b.table("Answering now (1) or not (0), worst first", f'label_replace(probe_success{{{web}}}, "service", "$1", "job", "integrations/blackbox/(.+)")', h=12, w=8,
            steps=[("red", None), ("green", 1)], description="Each service is asked once a minute where it answers itself: inside the cluster, or at its own address.")
    b.table("Availability over 7 days, worst first", f'label_replace(100 * avg_over_time(probe_success{{{web}}}[7d]), "service", "$1", "job", "integrations/blackbox/(.+)")', "percent", h=12, w=8,
            steps=[("red", None), ("yellow", 99), ("green", 99.9)])
    b.table("Answer time now", f'label_replace(probe_duration_seconds{{{web}}}, "service", "$1", "job", "integrations/blackbox/(.+)")', "s", h=12, w=8,
            steps=[("green", None), ("yellow", 2), ("red", 5)])
    b.row("Over time")
    b.graph("Services not answering", [(f'label_replace(probe_success{{{web}}} == 0, "service", "$1", "job", "integrations/blackbox/(.+)") + 1', "{{service}}")], w=24, h=7,
            description="A line appears only while a service does not answer.")
    b.graph("Answer time", [(f'label_replace(probe_duration_seconds{{{web}}}, "service", "$1", "job", "integrations/blackbox/(.+)")', "{{service}}")], "s", w=24, h=9)
    return b


BOARDS = {"pfsense.json": pfsense, "postgresql.json": postgresql, "kubernetes.json": kubernetes, "virtual-machines.json": machines, "service-health.json": services}


def main():
    stale = []
    for name, build in BOARDS.items():
        text = json.dumps(build().json(), indent=2) + "\n"
        path = OUT / name
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.write_text(text)
            print(f"written: {path.relative_to(OUT.parents[2])} ({len(build().panels)} panels)")
    if stale:
        sys.exit(f"stale dashboards, run scripts/grafana-dashboards.py: {', '.join(stale)}")


if __name__ == "__main__":
    main()
