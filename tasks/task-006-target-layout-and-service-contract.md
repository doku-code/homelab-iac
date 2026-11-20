---
title: TASK-006 — Target repository layout, OpenTofu toolchain and management Make targets
description: Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check).
published: true
tags:
- task
- in-progress
- layout
- opentofu
- make
editor: markdown
date: '2026-11-12T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-006 — Target repository layout, OpenTofu toolchain and management Make targets

> **ID:** TASK-006 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-12 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-006-target-layout-and-service-contract.md)

**Authorization:** OFFLINE_CODE. A task status never authorizes a live change by itself.

## Goal

Give the first new root a predictable home and a repeatable, approval-gated workflow. The service.yaml catalog schema is deferred to M003.

## Context

- [ARCH-platform](/docs/architecture/platform#target-repository-layout)
- [ADR-003](/docs/decisions/adr-003-opentofu-for-new-infrastructure), [ADR-005](/docs/decisions/adr-005-windmill-service-catalog)

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
