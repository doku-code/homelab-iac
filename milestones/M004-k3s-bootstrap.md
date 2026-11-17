---
id: M004
title: "k3s bootstrap"
summary: "The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl."
type: milestone
status: active
priority: high
created: 2026-11-12
updated: 2026-11-17
tags: [roadmap]
related_tasks: [TASK-015]
related_decisions: [ADR-011]
related: [ARCH-platform, DOC-project-overview, INV-new-proxmox-cluster-inventory]
depends_on: [M002]
completion_criteria: []
---

# M004 — k3s bootstrap

## Objective

Provide the application platform early, sized for current hardware and ready to add servers and agents.

**Completion criterion:** The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl.

Placement proposal: first server on the new `pve-lab` (.16), next node on `pve-core` (.11), a third etcd voter later; capacity in [INV-new-proxmox-cluster-inventory](../docs/investigations/new-proxmox-cluster-inventory.md).

## Scope

In scope:

- k3s VM(s) via OpenTofu, k3s via Ansible, embedded etcd ready for more servers
- Kubeconfig for the workstation and the runner, basic networking and ingress decision
- Initial availability documented separately from the later HA design

Out of scope:

- Persistent storage (M006)
- Databases inside the cluster used to bootstrap it

## Expected deliverables

- k3s root and role; admin access documented

## Dependencies

- M002

## Acceptance criteria

- [ ] `kubectl get nodes` healthy from the workstation
- [ ] Rebuilding a k3s VM from IaC succeeds

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
