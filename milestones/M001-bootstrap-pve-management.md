---
id: M001
title: "Bootstrap pve-management"
summary: "Existing infrastructure provisions and configures a management VM on pve-management automatically, with recoverable state and bootstrap secrets."
type: milestone
status: planned
priority: critical
created: 2026-11-12
updated: 2026-11-12
tags: [bootstrap, pve-management]
related_tasks: [TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012]
related_decisions: [ADR-002, ADR-003, ADR-004, ADR-005]
related: [ARCH-platform, INV-pve-management-bootstrap]
depends_on: []
completion_criteria: []
---

# M001 — Bootstrap pve-management

## Objective

Establish the independent management foundation on the fresh pve-management host.

Implementation plan: [INV-pve-management-bootstrap](../docs/investigations/pve-management-bootstrap.md).

**Completion criterion:** Existing infrastructure provisions and configures a management VM on pve-management automatically, with recoverable state and bootstrap secrets.

## Scope

In scope:

- Connectivity, scoped Proxmox API token and SSH access
- Reusable OpenTofu guest module and the management VM root
- Ansible baseline with the IaC toolchain and a dedicated Forgejo runner
- SOPS + age bootstrap secrets
- State management and backups
- Independent bootstrap/recovery runbook

Out of scope:

- Phase, Windmill and application services
- Joining pve-management to any cluster

## Expected deliverables

- modules/opentofu/proxmox-guest
- stacks/management/ root
- Ansible role for the management VM
- secrets/bootstrap/ with .sops.yaml
- Bootstrap and recovery runbook

## Dependencies

- M000 inventory of credentials and network facts (can start in parallel for offline code)

## Acceptance criteria

- [ ] A plan/apply from the existing runner or a workstation creates the management VM on pve-management
- [ ] A second run is a no-op (idempotent)
- [ ] Ansible converges the VM with the toolchain and a registered runner
- [ ] State and bootstrap secrets are backed up outside pve-management
- [ ] The runbook has been followed from a workstation at least once

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
