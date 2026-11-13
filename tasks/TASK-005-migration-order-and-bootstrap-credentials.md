---
id: TASK-005
title: "Migration order and bootstrap credential requirements"
summary: "Decide the service migration order and list every bootstrap credential and recovery prerequisite."
type: task
status: planned
priority: high
milestone: M000
created: 2026-11-12
updated: 2026-11-12
tags: [planning, migration]
depends_on: [TASK-002, TASK-003, TASK-004]
related: [ARCH-platform]
related_decisions: [ADR-001, ADR-004]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-005 — Migration order and bootstrap credential requirements

**Authorization:** READ_ONLY. A task status never authorizes a live change by itself.

## Goal

Turn the inventory into an executable migration sequence.

## Context

- TASK-002..004
- [ADR-001](../docs/decisions/ADR-001-rolling-infrastructure-rebuild.md)
- [ADR-004](../docs/decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)

## Acceptance criteria

- [ ] Ordered migration list with rationale, downtime and rollback per service
- [ ] Bootstrap credential list (names, owners, storage location type — no values)
- [ ] Hardware reclaim order (which host empties first)

## Verification

- Operator review

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
