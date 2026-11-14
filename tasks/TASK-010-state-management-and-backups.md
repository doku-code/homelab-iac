---
id: TASK-010
title: "OpenTofu state: one local authority, handed over to the workstation"
summary: "Keep new-root state local on the single operator workstation, move it from the Mac to mgmt-control-01, and never let an empty state recreate existing guests."
type: task
status: in-progress
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-14
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

Each root has exactly one writable state, on the operator workstation. Re-scoped by the operator on
2026-11-14: no remote backend, locking server or automated backups for now (single operator); the
legacy roots stay where they are until they are migrated.

## Context

- Nine legacy roots keep local state ([INV-legacy-inventory](../docs/investigations/legacy-inventory.md))
- Archived PG backend and Garage evaluations in docs/archive/codex-2026/docs/

## Acceptance criteria

- [ ] `pve-management-control` state copied to `mgmt-control-01` (0600, git-ignored), Mac copy retired
- [ ] `tofu state list` on the VM shows the image and VM 100; a plan from the VM reports no changes
- [x] `make mgmt-plan` refuses to run without a state file (tested in `tests/mgmt-control.py`)

## Verification

- `tofu state list` and a no-change `make mgmt-plan` on the VM

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Bootstrap strategy for new roots: local state + `mgmt-state-backup` (age, off-machine) | Implemented; refusal paths tested; no state exists yet | Makefile, ARCH-platform#state-management | 2026-11-12 |
| Backups of the nine legacy local states | Deferred by the operator (re-scope above) | — | 2026-11-14 |

## Completion summary

_Not completed._
