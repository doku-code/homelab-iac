---
id: M003
title: "Dedicated Forgejo deployment runner"
summary: "A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials."
type: milestone
status: active
priority: high
created: 2026-11-12
updated: 2026-11-17
tags: [roadmap]
related_tasks: [TASK-014]
related_decisions: [ADR-014, ADR-008]
related: [ARCH-platform, DOC-project-overview, INV-new-proxmox-cluster-inventory]
depends_on: [M002]
completion_criteria: []
---

# M003 — Dedicated Forgejo deployment runner

## Objective

Automate approved OpenTofu, Ansible, k3s and Helm jobs from Forgejo without giving CT301 deployment credentials.

**Completion criterion:** A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials.

Placement (operator, 2026-11-17): the bootstrap runner `deploy-runner-01` runs on `pve-core` (6 vCPU / 8 GiB;
`pve-management` was too small); design and runbook in [TASK-014](../tasks/TASK-014-bootstrap-deployment-runner-vm.md).

## Scope

In scope:

- Runner VM (OpenTofu `headless-vm` module) and Ansible role
- Registration with the current Forgejo; protected-ref, approval-gated workflows
- Scoped Proxmox and Kubernetes credentials
- State access for the roots the runner applies (TASK-010 decides the backend at that point)

Out of scope:

- Migrating Forgejo
- Credentials on CT301

## Expected deliverables

- Runner root, role and one approved workflow

## Dependencies

- M002

## Acceptance criteria

- [ ] A reviewed workflow plans and applies a disposable resource through the runner
- [ ] Validation jobs never receive deployment credentials

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
