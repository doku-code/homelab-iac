---
id: TASK-003
title: "Service dependency, network/DNS and data/backup map"
summary: "Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage."
type: task
status: planned
priority: high
milestone: M010
created: 2026-11-12
updated: 2026-11-14
tags: [inventory, dependencies, backup]
depends_on: [TASK-002]
related: [ARCH-platform]
related_decisions: []
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-003 — Service dependency, network/DNS and data/backup map

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
