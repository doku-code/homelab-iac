---
title: M002 — New Proxmox cluster (four nodes)
description: The new cluster doku-lab runs on pve-management, pve-core, pve-infra and the new pve-lab (.16), quorate, with its hardware and capacity inventoried.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-16T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M002 — New Proxmox cluster (four nodes)

> **ID:** M002 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-16 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M002-proxmox-compute-capacity.md)

## Objective

Form the new cluster on `pve-management` with freshly installed compute nodes, without disturbing `mgmt-control-01` or the old environment (`192.168.0.14`).

**Completion criterion:** the new cluster runs quorate with its nodes, hardware and capacity inventoried ([INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory)).

The operator went further than planned (2026-11-16): `pve-core`, a new `pve-infra` and a new `pve-lab` (.16)
joined, so the two-node quorum question disappeared.

## Scope

In scope:

- Confirm `pve-core` holds no workload or data to keep; read-only NVMe/disk inventory
- Guard legacy roots that target the `pve-core` address before reinstalling
- Clean Proxmox VE install, scoped API token, TLS trust, discovery
- Create the cluster on `pve-management`, join `pve-core`; quorum plan (QDevice evaluated)

Out of scope:

- Shared or distributed storage (M006, M011)
- HA claims for two nodes

## Expected deliverables

- Updated host inventory with the NVMe layout
- Repeatable install-and-join procedure for later reclaimed hosts

## Dependencies

- M001

## Acceptance criteria

- [x] `pve-core` (and `pve-infra`, new `pve-lab`) installed and joined; `pve-management` and VM 100 unaffected
- [x] Quorum documented: four votes, quorum 3, no QDevice needed
- [x] NVMe devices and free capacity of every node recorded

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Cluster quorate, 4/4 members | `pvecm status` (all nodes) | `doku-lab`, quorate, expected votes 4 | 2026-11-16 |
| Inventory | read-only audit | INV-new-proxmox-cluster-inventory | 2026-11-16 |
| VM 100 unaffected | `qm list`, `make mgmt-plan` from the VM | running; No changes | 2026-11-16 |

## Completion summary

Completed 2026-11-16 (operator installs and joins, verified read-only). Next: M003.
