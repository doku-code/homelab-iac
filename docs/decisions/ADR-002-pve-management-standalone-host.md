---
id: ADR-002
title: pve-management is a standalone bootstrap, orchestration and recovery host
summary: The fresh Proxmox host pve-management stays outside the compute cluster and runs only management VMs (IaC toolchain, runner, later Windmill/Phase).
type: decision
status: superseded
importance: 5
created: 2026-11-12
updated: 2026-11-14
tags: [decision, management, bootstrap, proxmox]
component: pve-management
related: [ARCH-platform]
related_tasks: [TASK-007, TASK-008, TASK-009]
related_milestones: [M001]
supersedes: []
superseded_by: [ADR-010]
---

# ADR-002: pve-management as a standalone host

> Superseded on 2026-11-14 by [ADR-010](ADR-010-new-proxmox-cluster-on-pve-management.md): pve-management founds the new cluster.

## Context

Recovery and orchestration should not depend on the compute cluster they manage. A fresh
Proxmox VE host, `pve-management`, is installed and empty.

## Decision

- `pve-management` remains independent of the future compute cluster (no cluster join).
- The hypervisor stays minimal: no application stacks on the host itself.
- The first guest is an Ubuntu Server management VM holding the IaC toolchain and a
  dedicated Forgejo runner; Windmill and Phase get their own VMs when resources allow.
- It is first provisioned from the existing infrastructure (current runner/workstation), so
  the management VM is never a prerequisite of its own creation.
- Access uses a dedicated, scoped Proxmox API token and SSH key; both must be verified, not assumed.

## Consequences

- Bootstrap must also run from an administrator workstation (disaster recovery path).
- Capacity of `pve-management` limits how many management services it hosts; placement of
  Windmill/Phase is confirmed per milestone.
