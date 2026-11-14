---
id: TASK-004
title: "Representative PBS restore test"
summary: "Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data."
type: task
status: planned
priority: high
milestone: M012
created: 2026-11-12
updated: 2026-11-14
tags: [backup, pbs, recovery]
depends_on: [TASK-003]
related: [ARCH-platform]
related_decisions: []
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-004 — Representative PBS restore test

> Roadmap 2026-11-14: moved from M000 to M012.

**Authorization:** LIVE_CHANGE — explicit operator approval of guest, target and network. A task status never authorizes a live change by itself.

## Goal

Prove backups are restorable before any migration relies on them.

## Context

- TASK-003 backup coverage
- PBS datastore and retention

## Acceptance criteria

- [ ] Restore to a new VMID on an isolated network, never over the original
- [ ] Boot and data check recorded; disposable guest removed only with approval

## Verification

- Restore task log and checks recorded in the evidence table

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
