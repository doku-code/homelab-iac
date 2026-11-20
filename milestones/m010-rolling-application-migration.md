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

- [ ] At least one legacy service migrated and its old workload retired
- [ ] A reclaimed host joined through the M002 procedure

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
