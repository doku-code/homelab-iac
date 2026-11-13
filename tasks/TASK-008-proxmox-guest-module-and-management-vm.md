---
id: TASK-008
title: "Reusable OpenTofu guest module and management VM root"
summary: "Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM."
type: task
status: planned
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [opentofu, pve-management]
depends_on: [TASK-006, TASK-007, TASK-010]
related: [ARCH-platform]
related_decisions: [ADR-002, ADR-003]
related_implementations: []
related_tests: []
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

- [ ] Module with tests using mocked providers (`tofu test`)
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
| | not verified | | |

## Completion summary

_Not completed._
