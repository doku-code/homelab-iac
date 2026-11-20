---
title: 'TASK-020 — Lean observability: Prometheus, Loki, Grafana and Alloy'
description: Prometheus, Loki and Grafana on k3s; Alloy collects a small allow-list of metrics and logs from the cluster and from every VM; Grafana state on the shared PostgreSQL.
published: true
tags:
- task
- completed
- observability
- prometheus
- loki
- grafana
- alloy
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-17T00:00:00.000Z'
---

# TASK-020 — Lean observability: Prometheus, Loki, Grafana and Alloy

> **ID:** TASK-020 · **Type:** task · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-020-lean-observability-prometheus-loki-grafana-and-alloy.md)

## Goal

Operator direction 2026-11-17: Grafana, Prometheus, Loki and Grafana Alloy with **useful metrics only**; no
stack that slows the platform down for numbers nobody reads.

## Context

- The legacy `services/monitoring` Compose stack (old environment) is untouched; this is the new platform's
  own stack under `services/observability`.
- Databases follow [ADR-015](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s): Grafana
  keeps its state in database `grafana` on the shared PostgreSQL.

## Design

- **One collector, Alloy, in two places.** Inside k3s one small Deployment reads through the Kubernetes API
  (kubelet and cAdvisor metrics, kube-state-metrics, pod logs): no DaemonSet, no host mounts, read-only
  rights without `nodes/proxy`. On every VM (`alloy_agent` role: k3s nodes, PostgreSQL members, storage,
  runner) it reads nine host collectors and the journal, and on PostgreSQL members the database (local
  socket, role `alloy`, `pg_monitor`, no password) and Patroni.
- **Allow-lists instead of everything.** Prometheus scrapes nothing but itself; the chart's discovery jobs,
  Alertmanager, Pushgateway and node exporter are off. Each source keeps a named list of metrics; a test
  checks that every dashboard panel and alert uses a metric that is collected. One sample per minute.
- **Storage:** Prometheus 15 days or 8 GB, Loki 7 days, both on `local-path` (rebuildable runtime data).
  Loki runs as one process without caches, canary or gateway.
- **Access:** `https://grafana.192.168.0.40.sslip.io/` for the administration LAN, login `admin` with
  `GRAFANA_ADMIN_PASSWORD` (store path `/monitoring`). VMs push to `metrics.` and `logs.192.168.0.40.sslip.io`
  (pinned in `/etc/hosts`): only the managed VM ranges, only the two write paths.
- **Dashboard** "Homelab overview" (provisioned from Git): hosts, PostgreSQL, Kubernetes, error logs.
  **Alerts** (9 rules in Prometheus): silent host, disk, memory, no or several primaries, missing member,
  replication lag, restarting or stuck pods, full volume.

## Acceptance criteria

- [x] Offline tests: pinned charts, allow-lists, least privilege, routes, agent templates, Make guards
- [x] Metrics from the cluster and from all six VMs; PostgreSQL and Patroni metrics; pod and host logs
- [x] Every dashboard panel returns data; every alert expression evaluates
- [x] Footprint measured

## Verification

```
make observability-check
scripts/secrets.py run /postgresql /monitoring -- make observability-deploy OBSERVABILITY_DEPLOY_APPROVED=yes
make observability-agents OBSERVABILITY_AGENTS_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/observability.py` | four pinned charts rendered with our values; Prometheus scrapes only itself; kube-state-metrics, kubelet and PostgreSQL allow-lists cover every dashboard and alert query; collector rights read-only without `nodes/proxy`; Grafana state in PostgreSQL over TLS with passwords from Secrets; routes; agent templates with and without PostgreSQL; Make guards | `make observability-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Deploy | Prometheus v3.16.0, Loki, Alloy v1.22.0, Grafana 13.3.1, kube-state-metrics: all pods Running | `make observability-deploy`, `kubectl get pods` | 2026-11-17 |
| Agents | Alloy 1.22.0 active on k3s-server-01, pg-01..03, storage-01, deploy-runner-01. First run failed on the PostgreSQL members (connection string must be a URL) and the k3s node got 403 (its own traffic arrives from the pod network); both fixed, second run clean | `make observability-agents` | 2026-11-17 |
| Footprint | **2,236 series** in total (hosts 1,182; PostgreSQL 453 after the allow-list, 1,778 before; cluster state 310; containers 186; Patroni 81); stack uses about 54 mCPU and 731 MiB | PromQL `count by (job)`, `kubectl top` | 2026-11-17 |
| Data | 6 hosts report; `patroni_primary` names pg-02; lag 0 on all members; 22 of 23 dashboard queries return data, the last ("Restarts in 24 h") is empty because nothing restarted; 9 alert expressions evaluate, none firing | script over the dashboard JSON | 2026-11-17 |
| Logs | Journal from 6 hosts and pod logs from 4 namespaces; about 750 host lines and 45 pod lines per minute | LogQL | 2026-11-17 |
| Grafana | Health `database: ok`; data sources Prometheus and Loki healthy; folder "Homelab" with the dashboard; 92 tables in database `grafana` | Grafana API, `psql` | 2026-11-17 |
| Access | Remote write from the workstation: 403; Prometheus UI through the ingestion host: 404 | `curl` | 2026-11-17 |

## Completion summary

Completed 2026-11-17. Not verified: the dashboard was checked through the API, not looked at in a browser.
Open: alert delivery (rules fire inside Prometheus and show in Grafana; nothing is sent anywhere yet, a
Discord contact point is the obvious next step); Proxmox host metrics (needs a read-only Proxmox identity,
which the operator has to approve); trusted certificate for the ingestion and Grafana names; the legacy
monitoring stack stays until its services migrate.
