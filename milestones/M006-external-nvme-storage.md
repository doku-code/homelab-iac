---
id: M006
title: "External NVMe-backed storage"
summary: "Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented."
type: milestone
status: completed
priority: high
created: 2026-11-12
updated: 2026-11-16
tags: [roadmap]
related_tasks: [TASK-017]
related_decisions: [ADR-012]
related: [ARCH-platform, DOC-project-overview, INV-new-proxmox-cluster-inventory]
depends_on: [M004]
completion_criteria: []
---

# M006 — External NVMe-backed storage

## Objective

Replace the rejected TrueNAS CSI idea with storage on the physical hosts' NVMe drives, external to the k3s cluster.

**Completion criterion:** Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented.

Inventory and options (Proxmox CSI over `local-lvm`, or a storage VM on `pve-core`): [INV-new-proxmox-cluster-inventory](../docs/investigations/new-proxmox-cluster-inventory.md#storage-options-for-m006-input-not-a-decision). No node has a spare NVMe yet.

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
