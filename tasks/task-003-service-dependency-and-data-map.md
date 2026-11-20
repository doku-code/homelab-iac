---
title: TASK-003 — Service dependency, network/DNS and data/backup map
description: Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage.
published: true
tags:
- task
- planned
- inventory
- dependencies
- backup
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-003 — Service dependency, network/DNS and data/backup map

> **ID:** TASK-003 · **Type:** task · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-003-service-dependency-and-data-map.md)

> Roadmap 2026-11-14: moved from M000 to M010.

**Authorization:** LIVE_READ. A task status never authorizes a live change by itself.

## Goal

Know what each service needs and what must be migrated or protected.

## Context

- Output of TASK-002
- pfSense, AdGuard (`home.arpa`), Caddy, public `doku-lab.net` DNS
- TrueNAS datasets and PBS jobs

## Acceptance criteria

- [ ] Table per service: dependencies, data locations, backup job, last successful backup, restore tested (yes/no)
- [ ] Network/DNS dependency diagram
- [ ] Manually configured services flagged

## Verification

- Review against live configuration (read-only)

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| | not verified | | |

## Completion summary

_Not completed._
