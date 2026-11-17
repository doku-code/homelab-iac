---
id: M003
title: "Dedicated Forgejo deployment runner"
summary: "A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials."
type: milestone
status: completed
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

- [x] A reviewed workflow plans and applies a disposable resource through the runner
- [x] Validation jobs never receive deployment credentials

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Reviewed workflow plans and applies a disposable resource | `deploy.yml` dispatch on `main` → `make deploy-runner-review` / `deploy-runner-approve` → dispatch apply | PASS: VM 9900 created (runs 92–93) and destroyed (runs 94–95) through the runner with `deploy-runner@pve!ci` (TASK-014) | 2026-11-17 |
| Validation jobs never receive deployment credentials | `tests/deploy-runner.py` (only `deploy.yml` targets `homelab-deploy`; other workflows reference no Proxmox/deploy secrets); runner's token readable only by `deploy` | PASS | 2026-11-17 |

## Completion summary

Completed 2026-11-17 with TASK-014: `deploy-runner-01` on pve-core runs approved OpenTofu workflows from
Forgejo with a pool-scoped Proxmox token; approval is out-of-band over SSH; CT301 stays validation-only.
Deferred: Kubernetes credentials (M004), shared-state roots (TASK-010); branch protection on `main` set 2026-11-17.
