---
id: ADR-010
title: "The new Proxmox cluster is founded on pve-management and grows with reclaimed hosts"
summary: "pve-management founds the new Proxmox cluster; the emptied pve-core joins first, every reclaimed host follows by the same repeatable process. Supersedes ADR-002."
type: decision
status: accepted
importance: 5
created: 2026-11-14
updated: 2026-11-14
tags: [decision, proxmox, cluster, pve-management, pve-core]
component: proxmox
topics: [proxmox, cluster, quorum, qdevice]
related: [ARCH-platform, ADR-001, ADR-009]
related_tasks: []
related_milestones: [M002, M011]
supersedes: [ADR-002]
superseded_by: []
---

# ADR-010: New Proxmox cluster founded on pve-management

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
