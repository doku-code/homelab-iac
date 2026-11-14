---
id: M012
title: "Backups and finalization"
summary: "Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired."
type: milestone
status: planned
priority: medium
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: [TASK-004, TASK-011, TASK-012]
related_decisions: [ADR-012, ADR-004, ADR-008]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M010]
completion_criteria: []
---

# M012 — Backups and finalization

## Objective

Review dependencies and recovery once the new platform has taken shape.

**Completion criterion:** Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired.

## Scope

In scope:

- Dependency and persistent-data review; backup workflows to TrueNAS
- PostgreSQL-aware backups, PBS, restore tests
- Bootstrap secrets (SOPS + age) and the recovery runbook; remote state if a second executor needs it

Out of scope:

- Destroying live data during earlier milestones (basic migration safety always applies)

## Expected deliverables

- Backup jobs, restore evidence, recovery runbook

## Dependencies

- M010

## Acceptance criteria

- [ ] A representative restore of each data class succeeded
- [ ] No workload depends on retired infrastructure

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
