---
id: M006
title: "Observability and platform improvements"
summary: "Prometheus, Loki and Grafana give useful health checks, dashboards, logs and alerts, outside the bootstrap path."
type: milestone
status: planned
priority: medium
created: 2026-11-12
updated: 2026-11-12
tags: [observability]
related_tasks: []
related_decisions: []
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M006 — Observability and platform improvements

## Objective

Introduce consolidated monitoring and operational visibility.

**Completion criterion:** Prometheus, Loki and Grafana give useful health checks, dashboards, logs and alerts, outside the bootstrap path.

## Scope

In scope:

- Prometheus, Loki, Grafana
- Health checks, dashboards, logs, alert delivery

Out of scope:

- Monitoring in the bootstrap critical path

## Expected deliverables

- services/ definitions for the observability stack
- Alert routes

## Dependencies

- M004

## Acceptance criteria

- [ ] Alerts reach the operator
- [ ] Logs and metrics cover migrated services

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
