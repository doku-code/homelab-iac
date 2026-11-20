---
title: M006 — External NVMe-backed storage
description: Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-16T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M006 — External NVMe-backed storage

> **ID:** M006 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-16 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M006-external-nvme-storage.md)

## Objective

Replace the rejected TrueNAS CSI idea with storage on the physical hosts' NVMe drives, external to the k3s cluster.

**Completion criterion:** Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented.

Inventory and options (Proxmox CSI over `local-lvm`, or a storage VM on `pve-core`): [INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory#storage-options-for-m006-input-not-a-decision). No node has a spare NVMe yet.

## Scope

In scope:

- NVMe hardware and capacity inventory on the hosts
- Selection of the simplest viable external service and its CSI driver for the real topology
- Deployment with IaC; StorageClasses supported by the driver (`nvme-block`, `nvme-shared` only if real)
- PVC provisioning, persistence across pod recreation, k3s VM restart/replacement
- `Retain` reclaim policy for critical volumes

Out of scope:

- TrueNAS CSI or iSCSI for live volumes (NFS from a storage VM on `pve-core` was chosen by the operator on 2026-11-17, TASK-017)
- Ceph before enough hardware exists (M011)
- NFS exports on hypervisors

## Expected deliverables

- Storage service root/role, CSI configuration, StorageClasses
- Failure-domain note (single host or otherwise)

## Dependencies

- M004

## Acceptance criteria

- [x] A test application keeps its data across pod deletion and k3s VM replacement
- [x] The storage failure domain is documented without HA claims

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Data survives pod deletion, k3s VM reboot and replacement | write through an `nvme-shared` PVC, read after each event | PASS (TASK-017) | 2026-11-17 |
| Failure domain documented | TASK-017 Design: one VM, one host, one NVMe, no backup yet | done | 2026-11-17 |

## Completion summary

Completed 2026-11-17 with TASK-017: `storage-01` (NFS, pve-core) and StorageClass `nvme-shared` for user data; `local-path` for app data on the node. Single failure domain, no backup until M012.
