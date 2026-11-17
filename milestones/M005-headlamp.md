---
id: M005
title: "Headlamp"
summary: "Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs."
type: milestone
status: completed
priority: high
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: [TASK-016]
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

- [x] Dashboard reachable from the administration LAN only (widened from workstation-only, TASK-016)
- [x] Nodes, workloads, PVC/PV/StorageClasses, events and logs visible

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| LAN-only access | `curl` from the workstation (200) and from a pod (403) | PASS (TASK-016) | 2026-11-17 |
| Objects visible | API through Headlamp with the admin token: nodes, pods, StorageClasses, PVs, events, logs | PASS (TASK-016); browser login not clicked through by the agent | 2026-11-17 |

## Completion summary

Completed 2026-11-17 with TASK-016: `https://headlamp.192.168.0.40.sslip.io/`, token login (Infisical `dev:/headlamp`), LAN only.
