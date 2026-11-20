---
title: 'ADR-010: New Proxmox cluster founded on pve-management'
description: pve-management founds the new Proxmox cluster; the emptied pve-core joins first, every reclaimed host follows by the same repeatable process. Supersedes ADR-002.
published: true
tags:
- decision
- accepted
- proxmox
- cluster
- pve-management
- pve-core
editor: markdown
date: '2026-11-16T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# ADR-010: New Proxmox cluster founded on pve-management

> **ID:** ADR-010 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-16 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-010-new-proxmox-cluster-on-pve-management.md)

## Context

ADR-002 kept `pve-management` standalone. The operator has since emptied `pve-core` (Ryzen 7 6800H,
8C/16T, 32 GB DDR5; workloads moved to `pve-lab`) and wants one new Proxmox environment that grows as
machines are reclaimed, instead of a separate management island.

## Decision

- `pve-management` (192.168.0.10) is the founding node of the new cluster. It keeps running
  `mgmt-control-01` (VM 100, ADR-009) unchanged while the cluster is created and joined.
- `pve-core` is reinstalled cleanly (after confirming its disks hold nothing to keep) and is the first
  node to join. Each later reclaimed host joins through the same repeatable procedure: install, scoped
  API access, read-only discovery, join, then OpenTofu-managed guests.
- Two nodes have no quorum tolerance: losing either one blocks cluster writes. An external QDevice (or a
  third node) is evaluated in M002; two hosts never imply automatic HA.
- Joining a cluster creates no shared storage. Each host keeps its local NVMe storage; shared or
  distributed storage is an explicit layer (ADR-012).
- Hypervisors stay minimal: no application stacks or ad-hoc NFS exports on Proxmox hosts.

## Consequences

- Cluster creation, joins and quorum settings are operator-approved changes (M002, TASK-013).
- Legacy roots whose endpoint is a reclaimed host's address must be guarded before that host is
  reinstalled, as was done for 192.168.0.10.
- Recovery of `mgmt-control-01` no longer assumes a standalone host; it still never depends on the
  services it hosts (ADR-008).

## Outcome (2026-11-16)

Cluster `doku-lab` exists with four nodes: `pve-management` (.10), `pve-core` (.11, ThinkStation P350
Tiny), a **new** `pve-infra` (.12, Celeron N5095A; a fresh install reusing the retired host's name and
address) and a **new** `pve-lab` (.16, Ryzen 7 6800H). The old `pve-lab` (192.168.0.14, Ryzen 9 9950X3D)
stays outside and keeps the old services; once emptied it is reinstalled as `pve-compute` and joined.
Facts: [INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory).
