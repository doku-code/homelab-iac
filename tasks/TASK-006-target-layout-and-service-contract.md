---
id: TASK-006
title: "Target repository layout, OpenTofu toolchain and service catalog schema"
summary: "Create the target layout (modules/, stacks/, services/, windmill/), pin OpenTofu, and define the service.yaml schema with offline validation."
type: task
status: planned
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [layout, opentofu, service-catalog]
depends_on: [TASK-001]
related: [ARCH-platform]
related_decisions: [ADR-003, ADR-005]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-006 — Target repository layout, OpenTofu toolchain and service catalog schema

**Authorization:** OFFLINE_CODE. A task status never authorizes a live change by itself.

## Goal

Give every new component a predictable home and a machine-readable contract Windmill can turn into a form.

## Context

- [ARCH-platform](../docs/architecture/platform.md#target-repository-layout)
- [ADR-003](../docs/decisions/ADR-003-opentofu-for-new-infrastructure.md), [ADR-005](../docs/decisions/ADR-005-windmill-service-catalog.md)

## Acceptance criteria

- [ ] Directories exist with READMEs; legacy paths untouched
- [ ] OpenTofu version pinned and installed by `make setup-controller` (or a dedicated target)
- [ ] `services/_schema/service.schema.json` plus one example service validated offline in CI
- [ ] Generic `make service-validate SERVICE=<name>` target

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
