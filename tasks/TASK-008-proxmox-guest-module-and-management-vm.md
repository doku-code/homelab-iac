---
id: TASK-008
title: "Reusable OpenTofu guest module and management VM root"
summary: "Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM."
type: task
status: in-progress
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-14
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
| Allocation confirmed (VMID 100, 192.168.0.39/24, 8 vCPU, 8 GiB, 120 GiB with discard, Ubuntu 26.04) | Recorded in private tfvars + example; root validates | INV-pve-management-bootstrap | 2026-11-14 |
| Readiness pass: CPU type `host`, 10 GiB proposed; discovery re-run (VMID 100 free, no missing privileges); `make mgmt-plan` | Plan: 2 to add (image download + VM 100), 0 change, 0 destroy; saved plan SHA256 `32cc53fb…4815b` | `make mgmt-check`, `tests/mgmt-control.py` | 2026-11-14 |
| `make mgmt-apply` of that plan (operator approval) | Apply complete: 2 added, 0 changed, 0 destroyed; image download 32 s; VM 100 created in 15m10s (only warning: guest agent not yet installed). SSH key login works; Ubuntu 26.04.1, kernel 7.0.0-38, 8 vCPU with AVX2, 10 GiB, 120 GiB disk, DNS 192.168.0.20; cloud-init done (only a deprecation notice from the Proxmox-generated config). State local and git-ignored | SSH checks | 2026-11-14 |
| Re-plan after apply | No changes, infrastructure matches the configuration (refresh waits ~15 min for the guest agent until `mgmt-configure` installs it) | `make mgmt-plan` | 2026-11-14 |
| Reviewed plan on pve-management | not verified (next step: `make mgmt-plan`) | — | — |

## Completion summary

_Not completed._
