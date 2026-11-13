---
id: ADR-003
title: OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually
summary: New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan.
type: decision
status: accepted
importance: 4
created: 2026-11-12
updated: 2026-11-12
tags: [decision, opentofu, terraform]
component: infrastructure
related: [ARCH-platform]
related_tasks: [TASK-006, TASK-010]
related_milestones: [M001]
supersedes: []
superseded_by: []
---

# ADR-003: OpenTofu for new infrastructure

## Context

The legacy roots under `terraform/stacks/` use Terraform with the `bpg/proxmox` provider and
keep their live state as local files beside the code. The target stack prefers OpenTofu
(open-source licence, compatible language).

## Decision

- Every new root (starting with `terraform/stacks/pve-management-control`) uses OpenTofu and the
  `bpg/proxmox` provider, pinned in its own OpenTofu lock file. New roots stay under `terraform/stacks/`
  and reuse `terraform/modules/*`; shared modules carry no `required_version`, each root pins its engine.
- Legacy Terraform roots are not converted in bulk. A root moves to OpenTofu only when it is
  touched for migration, after `tofu plan` shows no changes against its existing state.
- Roots whose resources are retired are archived with their state backed up, never deleted blindly.

## Consequences

- Two binaries coexist during the rebuild; Make targets and CI name the tool per root.
- State compatibility is verified per root, not assumed.
