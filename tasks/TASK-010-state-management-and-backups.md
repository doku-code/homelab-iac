---
id: TASK-010
title: "OpenTofu state management and backups"
summary: "Choose the state backend for new roots and back up the existing legacy local states outside the operator workstation."
type: task
status: planned
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [state, backup]
depends_on: [TASK-006]
related: [ARCH-platform]
related_decisions: [ADR-003]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-010 — OpenTofu state management and backups

**Authorization:** LIVE_CHANGE (backup storage) with approval. A task status never authorizes a live change by itself.

## Goal

No state exists only on one laptop; each root has one writable authority.

## Context

- Nine legacy roots keep local state ([INV-legacy-inventory](../docs/investigations/legacy-inventory.md))
- Archived PG backend and Garage evaluations in docs/archive/codex-2026/docs/

## Acceptance criteria

- [ ] Decision record for the new-root backend (state must not depend on services it recreates)
- [ ] Encrypted, dated backups of every legacy local state stored off-host
- [ ] Restore of one state backup verified with a no-change plan

## Verification

- Backup checksum check
- No-change plan after restore

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
