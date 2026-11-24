---
title: TASK-034 — VictoriaMetrics replaces Prometheus; vmalert evaluates the rules
description: VictoriaMetrics single node stores the metrics Alloy pushes, vmalert evaluates the alert rules, kube-state-metrics is its own chart; Prometheus is retired
published: true
tags:
- task
- completed
- observability
- victoriametrics
editor: markdown
date: '2026-11-24T00:00:00.000Z'
dateCreated: '2026-11-24T00:00:00.000Z'
---

# TASK-034 — VictoriaMetrics replaces Prometheus; vmalert evaluates the rules

> **ID:** TASK-034 · **Type:** task · **Status:** completed · **Updated:** 2026-11-24 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-034-victoriametrics-replaces-prometheus-vmalert-evaluates-the-ru.md)

## Goal

The operator asked for VictoriaMetrics instead of Prometheus and for a check that the cluster does not collect
series twice. Metrics are stored by one VictoriaMetrics single-node, the alert rules are evaluated by vmalert,
kube-state-metrics is its own chart; the Prometheus chart is no longer deployed.

## Context

- Collection was already an allow-list (TASK-020): Alloy scrapes the kubelets (four metric names), cAdvisor
  (six, pods only), kube-state-metrics (fourteen families) and the switch, and pushes them. The control-plane
  endpoints of k3s, which all expose the same registry and are the usual source of duplicated series, are not
  scraped at all. Measured before the change: 3,924 active series, 76 MB on disk for six days.
- Nothing changes for the agents on the VMs: same address, same path (`/api/v1/write`).
- Grafana keeps the data source uid `prometheus` (type Prometheus, pointed at VictoriaMetrics): the dashboards
  need no change. The widget API of the dashboard reads the same query API.
- `HostSilent` used `timestamp()`, which can never be older than the staleness interval, so it could not fire;
  it now uses MetricsQL `lag()`.
- Firing alerts go to the Alertmanager of the vmalert chart, which posts them to the operator's Discord channel: the
  webhook of the old monitoring VM, still in the store (`DISCORD_ALERT_WEBHOOK`, path `/`), mounted from the Secret
  `alertmanager-discord` that `make observability-deploy` writes. Same routing as before: critical repeats hourly, the rest every four hours.
- Retention 90 days (was 15).

## Acceptance criteria

- [x] VictoriaMetrics, vmalert and kube-state-metrics run from Argo CD; Alloy in the cluster and the VMs write to VictoriaMetrics.
- [x] Grafana and the dashboard's widget API start on the new address; the rules are loaded by vmalert (the rendering of the panels in a browser is the operator's check).
- [x] The history held by Prometheus is copied.
- [x] Prometheus's workloads are removed from the cluster.
- [x] The volume `prometheus-server` is deleted (operator's word, 2026-11-24).
- [x] Alerts reach Discord.
- [x] The switch dashboard draws the front panel.
- [x] Offline tests.

## Verification

```
make observability-check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/observability.py | Pinned charts, VictoriaMetrics scrapes nothing, retention, vmalert flags and rules, kube-state-metrics allow-list, ingest route, every dashboard and alert metric is collected | `make observability-check` | PASS (2026-11-24) |
| tests/argocd.py | Chart pins of the application equal the Makefile's, allowed repositories | `.venv/bin/python tests/argocd.py` | PASS (2026-11-24) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Deployment | `victoria-metrics-0`, `vmalert`, `kube-state-metrics` Running; application `monitoring` Healthy | `kubectl -n monitoring get pods`, commits 9e30d89 and a66f0b4 | 2026-11-24 |
| Grafana | first start refused the renamed data source (`data source with the same uid already exists`); fixed with `deleteDatasources`, pod 1/1 | a66f0b4 | 2026-11-24 |
| Series arriving | seven jobs, 8 hosts report `node_load1`, each less than 21 s ago (`lag()`) | query API of VictoriaMetrics | 2026-11-24 |
| Rules | 13 rules loaded by vmalert, no evaluation error | `/api/v1/rules` of vmalert | 2026-11-24 |
| History | `Import finished`, 32,921,308 samples, first sample of `node_load1` from 2026-11-17 | `vmctl remote-read` in a one-off pod | 2026-11-24 |
| Prometheus removed | Deployments, Services, ConfigMap, accounts and cluster roles of the release deleted; the volume `prometheus-server` is kept | `kubectl delete -l app.kubernetes.io/instance=prometheus` | 2026-11-24 |
| Use | VictoriaMetrics 199 Mi right after the import, vmalert 12 Mi, kube-state-metrics 28 Mi | `kubectl top` | 2026-11-24 |
| Discord | test alert `DeliveryTest` posted: `alertmanager_notifications_total{integration="discord"} 1`, every `failed` counter 0 | metrics of Alertmanager | 2026-11-24 |
| Front panel | canvas panel rendered with the 16 ports in place and coloured by link state (ports 2, 9 to 13 and 15 gray, the others green) | screenshot of `/d/switch` through geckodriver | 2026-11-24 |
| Old volume | `persistentvolumeclaim "prometheus-server" deleted` | `kubectl -n monitoring delete pvc` | 2026-11-24 |
| Snapshot sidecar | 63 `Failed to watch` lines in 10 minutes before, 0 in 3 minutes after the snapshot controller and its CRDs | logs of `csi-snapshotter` | 2026-11-24 |

## Completion summary

Done on 2026-11-24: VictoriaMetrics, vmalert and Alertmanager run from Argo CD with the copied history, alerts reach
Discord, Prometheus and its volume are gone. Not verified: that the drawing matches the physical order of the
ports (odd numbers assumed on the top row).
