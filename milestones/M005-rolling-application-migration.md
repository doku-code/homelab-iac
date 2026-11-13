---
id: M005
title: "Rolling application migration"
summary: "Existing services are progressively replaced without a complete homelab outage; emptied hosts are reinstalled and joined."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-12
tags: [migration]
related_tasks: []
related_decisions: [ADR-001, ADR-006]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M005 — Rolling application migration

## Objective

Gradually replace existing workloads, one service at a time.

**Completion criterion:** Existing services are progressively replaced without a complete homelab outage; emptied hosts are reinstalled and joined.

## Scope

In scope:

- Per service: dependencies, reproducible deployment, replacement, data migration, validation, monitoring/backup, cutover, rollback, retirement
- Reinstall and join emptied physical hosts

Out of scope:

- Migrating several services in one change

## Expected deliverables

- One task per service, created from the M000 migration order

## Dependencies

- M000
- M003
- M004

## Acceptance criteria

- [ ] Each migrated service has passed validation, has backups and monitoring, and a recorded rollback path

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
