---
title: M011 — Ceph and infrastructure expansion
description: With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts.
published: true
tags:
- milestone
- planned
- roadmap
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M011 — Ceph and infrastructure expansion

> **ID:** M011 · **Type:** milestone · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M011-ceph-and-expansion.md)

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
