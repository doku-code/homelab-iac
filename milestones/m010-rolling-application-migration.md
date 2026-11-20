---
title: M010 — Rolling application migration
description: Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster.
published: true
tags:
- milestone
- planned
- roadmap
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M010 — Rolling application migration

> **ID:** M010 · **Type:** milestone · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M010-rolling-application-migration.md)

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

- [x] At least one legacy service migrated and its old workload retired
- [ ] A reclaimed host joined through the M002 procedure

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Legacy service migrated, old workload retired | [TASK-027](/tasks/task-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab), [TASK-029](/tasks/task-029-wiki-js-3-on-k3s-showing-this-repository-s-documentation) | Homepage and the wiki run on k3s under Argo CD behind Authentik; CT201 and CT202 are stopped (kept, not deleted). The applications hosted on TrueNAS are outside this milestone by the operator's decision of 2026-11-20 | 2026-11-20 |
| Reclaimed host joined | | not started: the old host still runs the legacy Caddy, Vaultwarden, the Tailscale routers and the migration runner | |

## Completion summary

_Not completed._
