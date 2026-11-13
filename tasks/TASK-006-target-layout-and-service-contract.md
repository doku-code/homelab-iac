---
id: TASK-006
title: "Target repository layout, OpenTofu toolchain and management Make targets"
summary: "Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check)."
type: task
status: in-progress
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [layout, opentofu, make]
depends_on: [TASK-001]
related: [ARCH-platform]
related_decisions: [ADR-003, ADR-005]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-006 — Target repository layout, OpenTofu toolchain and management Make targets

**Authorization:** OFFLINE_CODE. A task status never authorizes a live change by itself.

## Goal

Give the first new root a predictable home and a repeatable, approval-gated workflow. The service.yaml catalog schema is deferred to M003.

## Context

- [ARCH-platform](../docs/architecture/platform.md#target-repository-layout)
- [ADR-003](../docs/decisions/ADR-003-opentofu-for-new-infrastructure.md), [ADR-005](../docs/decisions/ADR-005-windmill-service-catalog.md)

## Acceptance criteria

- [x] New OpenTofu root under `terraform/stacks/` reusing `terraform/modules/*`; no parallel tree; legacy paths untouched
- [x] OpenTofu 1.13.9 pinned: CI (SHA256), management VM playbook (release SHA256SUMS), workstation via Homebrew
- [x] `mgmt-check`, `mgmt-discover`, `mgmt-plan`, `mgmt-apply`, `mgmt-configure`, `mgmt-state-backup` with saved plan + approval + plan hash
- [ ] CI validates new OpenTofu roots offline (step added; first CI run pending)

## Verification

- Offline schema test
- tofu fmt -check
- harness check

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `make mgmt-check` (fmt, validate, 5 mocked tofu tests, Ansible syntax, guard tests) | PASS | local run | 2026-11-12 |
| Refusal paths of mgmt-* targets in a sandbox with fake binaries | PASS | tests/mgmt-control.py | 2026-11-12 |
| CI step `Validate OpenTofu root …` | not verified (not pushed) | — | 2026-11-12 |

## Completion summary

_Not completed._
