---
title: M005 — Headlamp
description: Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M005 — Headlamp

> **ID:** M005 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M005-headlamp.md)

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
