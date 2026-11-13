---
id: TASK-008
title: "Reusable OpenTofu guest module and management VM root"
summary: "Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM."
type: task
status: in-progress
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [opentofu, pve-management]
depends_on: [TASK-006, TASK-007, TASK-010]
related: [ARCH-platform]
related_decisions: [ADR-002, ADR-003]
related_implementations: []
related_tests: [terraform/stacks/pve-management-control/tests/profile.tftest.hcl, tests/mgmt-control.py, tests/vm-profiles.py]
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-008 — Reusable OpenTofu guest module and management VM root

**Authorization:** OFFLINE_CODE, then LIVE_CHANGE apply with approval. A task status never authorizes a live change by itself.

## Goal

Provision the management VM declaratively and idempotently.

## Context

- Plan, reusable assets and acceptance tests: [INV-pve-management-bootstrap](../docs/investigations/pve-management-bootstrap.md)
- TASK-006 layout
- TASK-007 access
- Legacy `terraform/examples/cloud-image-vm` as a reference only

## Acceptance criteria

- [x] Existing `headless-vm` module reused (engine-agnostic, legacy defaults kept); root tested with mocked provider (`tofu test`)
- [ ] Root plans the management VM with explicit placement/storage/network inputs
- [ ] Apply (approved) creates it; second plan shows no changes

## Verification

- tofu fmt/validate/test offline
- Approved plan and apply on pve-management

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `tofu test` (contract + 4 refusal cases) | PASS 5/5 | terraform/stacks/pve-management-control/tests | 2026-11-12 |
| Legacy mocked Terraform tests after the module change | PASS 13/13 | tests/vm-profiles.py | 2026-11-12 |
| Reviewed plan on pve-management | not verified (needs TASK-007) | — | 2026-11-12 |

## Completion summary

_Not completed._
