---
id: TASK-034
title: VictoriaMetrics replaces Prometheus; vmalert evaluates the rules
summary: VictoriaMetrics single node stores the metrics Alloy pushes, vmalert evaluates the alert rules, kube-state-metrics is its own chart; Prometheus is retired
type: task
status: in-progress
priority: medium
milestone: M010
created: 2026-11-24
updated: 2026-11-24
tags: [observability, victoriametrics]
depends_on: []
related: [TASK-020, TASK-031]
related_decisions: []
related_implementations:
  - services/observability/victoriametrics.yaml
  - services/observability/vmalert.yaml
  - services/observability/kube-state-metrics.yaml
  - services/argocd/apps/monitoring.yaml
  - services/observability/cluster.alloy
related_tests:
  - tests/observability.py
  - tests/argocd.py
tests_justification: ""
verification_commands:
  - make observability-check
evidence: []
---

# VictoriaMetrics replaces Prometheus; vmalert evaluates the rules

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
- No notification channel yet (`-notifier.blackhole`): alerts show in Grafana only.
- Retention 90 days (was 15).

## Acceptance criteria

- [ ] VictoriaMetrics, vmalert and kube-state-metrics run from Argo CD; Alloy in the cluster and the VMs write to VictoriaMetrics.
- [ ] Grafana dashboards and the dashboard's cards show data; the rules are loaded by vmalert.
- [ ] The history held by Prometheus is copied.
- [ ] Prometheus's workloads are removed from the cluster (its volume on the operator's word).
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

## Completion summary

In progress. Remaining: deploy, verify, copy the history, remove the Prometheus workloads.
