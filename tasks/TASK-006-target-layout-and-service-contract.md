---
id: TASK-006
title: "Target repository layout, OpenTofu toolchain and management Make targets"
summary: "Create the target layout (modules/, stacks/), pin OpenTofu in the controller setup, add mgmt-* Make targets and offline CI validation for new roots."
type: task
status: planned
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

- [ ] Directories exist with READMEs; legacy paths untouched
- [ ] OpenTofu version pinned and installed by `make setup-controller` (or a dedicated target)
- [ ] `mgmt-check`, `mgmt-plan`, `mgmt-apply` targets reusing the saved-plan + explicit-approval pattern
- [ ] CI validates new OpenTofu roots offline (fmt, validate with backend disabled, `tofu test`)

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
| | not verified | | |

## Completion summary

_Not completed._
