---
title: 'ADR-003: OpenTofu for new infrastructure'
description: New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan.
published: true
tags:
- decision
- accepted
- opentofu
- terraform
editor: markdown
date: '2026-11-12T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-003: OpenTofu for new infrastructure

> **ID:** ADR-003 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-12 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-003-opentofu-for-new-infrastructure.md)

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
