---
id: M006
title: "External NVMe-backed storage"
summary: "Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: []
related_decisions: [ADR-012]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M004]
completion_criteria: []
---

# M006 — External NVMe-backed storage

## Objective

Replace the rejected TrueNAS CSI idea with storage on the physical hosts' NVMe drives, external to the k3s cluster.

**Completion criterion:** Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented.

## Scope

In scope:

- NVMe hardware and capacity inventory on the hosts
- Selection of the simplest viable external service and its CSI driver for the real topology
- Deployment with IaC; StorageClasses supported by the driver (`nvme-block`, `nvme-shared` only if real)
- PVC provisioning, persistence across pod recreation, k3s VM restart/replacement
- `Retain` reclaim policy for critical volumes

Out of scope:

- TrueNAS CSI, NFS or iSCSI for live volumes
- Ceph before enough hardware exists (M011)
- NFS exports on hypervisors

## Expected deliverables

- Storage service root/role, CSI configuration, StorageClasses
- Failure-domain note (single host or otherwise)

## Dependencies

- M004

## Acceptance criteria

- [ ] A test application keeps its data across pod deletion and k3s VM replacement
- [ ] The storage failure domain is documented without HA claims

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
