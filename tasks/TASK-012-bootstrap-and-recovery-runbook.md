---
id: TASK-012
title: "Independent bootstrap and recovery runbook"
summary: "Write and exercise the runbook that rebuilds the management VM from a clean workstation."
type: task
status: planned
priority: high
milestone: M012
created: 2026-11-12
updated: 2026-11-14
tags: [recovery, runbook]
depends_on: [TASK-008, TASK-009, TASK-010, TASK-011]
related: [ARCH-platform]
related_decisions: [ADR-010, ADR-004, ADR-008]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-012 — Independent bootstrap and recovery runbook

> Deferred by the operator on 2026-11-14: not a prerequisite for the rebuild (moved from M001 to M012, backups and finalization).

**Authorization:** LIVE_CHANGE with approval. A task status never authorizes a live change by itself.

## Goal

Recovery of the management layer is documented and proven.

## Context

- TASK-008..011

## Acceptance criteria

- [ ] Runbook lists prerequisites (repo mirror, age key, backups) and exact commands
- [ ] Followed once end to end from a workstation; gaps fixed

## Verification

- Recorded run

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
