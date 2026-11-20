---
title: M004 — k3s bootstrap
description: The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M004 — k3s bootstrap

> **ID:** M004 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M004-k3s-bootstrap.md)

## Objective

Provide the application platform early, sized for current hardware and ready to add servers and agents.

**Completion criterion:** The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl.

Placement proposal: first server on the new `pve-lab` (.16), next node on `pve-core` (.11), a third etcd voter later; capacity in [INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory).

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

- [x] `kubectl get nodes` healthy from the workstation
- [x] Rebuilding a k3s VM from IaC succeeds

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| `kubectl get nodes` healthy from the workstation | `kubectl get nodes -o wide` (context doku-lab) | PASS: k3s-server-01 Ready, control-plane,etcd, v1.35.8+k3s1 (TASK-015) | 2026-11-17 |
| Rebuilding a k3s VM from IaC succeeds | `make k3s-cluster-plan K3S_CLUSTER_REPLACE=k3s-server-01` → apply → hostkeys → configure | PASS: replaced and Ready again in 191 s; plan afterwards: No changes (TASK-015) | 2026-11-17 |

## Completion summary

Completed 2026-11-17 with TASK-015: single-server k3s (embedded etcd) on pve-lab, reachable with kubectl,
rebuildable from IaC. Initial availability is one server (no HA); more servers are tfvars entries.
Ingress/LB decision: bundled Traefik + ServiceLB for now. Deferred: runner kubeconfig with scoped RBAC,
local-path vs ADR-012 (M006), etcd snapshot backups (M012).
