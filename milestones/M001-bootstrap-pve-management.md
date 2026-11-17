---
id: M001
title: "Management workstation"
summary: "Existing infrastructure provisions and configures the management workstation VM on pve-management from IaC, and operations move to it."
type: milestone
status: active
priority: critical
created: 2026-11-12
updated: 2026-11-16
tags: [bootstrap, pve-management]
related_tasks: [TASK-006, TASK-007, TASK-008, TASK-009, TASK-010]
related_decisions: [ADR-009, ADR-003, ADR-010, ADR-008]
related: [ARCH-platform, INV-pve-management-bootstrap]
depends_on: []
completion_criteria: []
---

# M001 — Management workstation

## Objective

Establish the independent management foundation on the fresh pve-management host.

Implementation plan: [INV-pve-management-bootstrap](../docs/investigations/pve-management-bootstrap.md).

**Completion criterion:** Existing infrastructure provisions and configures the management workstation
VM on pve-management from IaC, and the operator works from it.

Re-scoped by the operator on 2026-11-14: the state stays local on the workstation; SOPS bootstrap
secrets (TASK-011) and the recovery runbook (TASK-012) are deferred to M012. No Forgejo runner on the
management VM (dedicated runner: M003). The VM is a genuine Ubuntu Desktop installed from the official ISO
(ADR-009); the first Ubuntu Server-based VM was replaced on 2026-11-14.

## Scope

In scope:

- Connectivity, scoped Proxmox API token, TLS trust and SSH access
- OpenTofu root `terraform/stacks/pve-management-control`: Desktop ISO, VM 100, autoinstall
- Ansible baseline and `admin_workstation` role: toolchain, Zed, Claude Code, Codex, GNOME Remote Login
- Local OpenTofu state, handed over from the Mac to the workstation

Out of scope:

- Phase, Windmill and application services
- Creating the new Proxmox cluster (M002, [ADR-010](../docs/decisions/ADR-010-new-proxmox-cluster-on-pve-management.md))

## Expected deliverables

- `terraform/stacks/pve-management-control` (Desktop ISO + autoinstall)
- `ansible/playbooks/configure-mgmt-control.yml` and `ansible/roles/admin_workstation`
- [Handoff](../docs/handoff.md) for sessions on the workstation

## Dependencies

- None

## Acceptance criteria

- [x] A plan/apply from a workstation creates the management VM on pve-management (TASK-008, first install)
- [x] The Ubuntu Desktop VM is installed from the official ISO; a second plan is a no-op (TASK-008)
- [x] Ansible converges the VM; a second run reports no changes (TASK-009)
- [ ] Thincast RDP, Zed, Claude Code, Codex, OpenTofu, Ansible, Git and Forgejo access work as `ubuntu` (TASK-009)
- [x] The OpenTofu state is handed over to the VM and recognized there (TASK-010)

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Desktop install, no-op plan | `make mgmt-plan` (Mac, then VM) | No changes | 2026-11-16 |
| Convergence + idempotency | `make mgmt-configure` ×2 | changed=0 on rerun | 2026-11-14 |
| State handover | `tofu state list` + plan on the VM | 2 resources, No changes | 2026-11-16 |
| Thincast two-stage login | operator | not verified | |

## Completion summary

_Not completed._
