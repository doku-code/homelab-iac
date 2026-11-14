---
id: M011
title: "Ceph and infrastructure expansion"
summary: "With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts."
type: milestone
status: planned
priority: medium
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: []
related_decisions: [ADR-012, ADR-013, ADR-010]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M010]
completion_criteria: []
---

# M011 — Ceph and infrastructure expansion

## Objective

Grow availability once the hardware supports it.

**Completion criterion:** With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts.

## Scope

In scope:

- Evaluate Ceph (Proxmox-integrated or independent): OSD placement, quorum, network bandwidth
- RBD and CephFS through Ceph CSI; data migration of selected PVCs
- PostgreSQL standbys across hosts; k3s control-plane expansion

Out of scope:

- A fragile Ceph on too few nodes

## Expected deliverables

- Ceph design record and deployment

## Dependencies

- M010

## Acceptance criteria

- [ ] Ceph health and failure tests documented
- [ ] A PVC migrated with its application validated

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
