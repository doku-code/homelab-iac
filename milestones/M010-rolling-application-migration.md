---
id: M010
title: "Rolling application migration"
summary: "Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: [TASK-003, TASK-005]
related_decisions: [ADR-001, ADR-011, ADR-012]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M009]
completion_criteria: []
---

# M010 — Rolling application migration

## Objective

Migrate the legacy services and reclaim their hardware.

**Completion criterion:** Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster.

## Scope

In scope:

- Per workload: deployment definition, Kubernetes resources, NVMe-backed PVCs, data migration, database and secrets, validation, cutover, retirement
- Observability (Prometheus, Loki, Grafana) deployed when the first migrated applications need it
- Reclaimed hosts: reinstall, join, add k3s and storage capacity

Out of scope:

- Destroying an original before its replacement works

## Expected deliverables

- Per-service migration records

## Dependencies

- M009

## Acceptance criteria

- [ ] At least one legacy service migrated and its old workload retired
- [ ] A reclaimed host joined through the M002 procedure

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
