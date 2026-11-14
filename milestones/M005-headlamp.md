---
id: M005
title: "Headlamp"
summary: "Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: []
related_decisions: [ADR-011]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M004]
completion_criteria: []
---

# M005 — Headlamp

## Objective

Get graphical Kubernetes administration before the storage, database and secrets platforms are deployed, to observe them.

**Completion criterion:** Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs.

## Scope

In scope:

- Official Helm chart, pinned version
- Kubernetes RBAC authentication; access from trusted administration networks only

Out of scope:

- Replacing Argo CD or Windmill
- Making kubectl depend on Headlamp

## Expected deliverables

- Helm values and access procedure

## Dependencies

- M004

## Acceptance criteria

- [ ] Dashboard reachable from the workstation only
- [ ] Nodes, workloads, PVC/PV/StorageClasses, events and logs visible

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
