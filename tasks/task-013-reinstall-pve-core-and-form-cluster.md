---
title: TASK-013 — Reinstall pve-core and form the new Proxmox cluster
description: Confirm the emptied pve-core holds nothing to keep, inventory its NVMe, reinstall Proxmox VE, create the cluster on pve-management and join pve-core with an explicit two-node quorum plan.
published: true
tags:
- task
- completed
- compute
- proxmox
- cluster
- pve-core
- m002
editor: markdown
date: '2026-11-16T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# TASK-013 — Reinstall pve-core and form the new Proxmox cluster

> **ID:** TASK-013 · **Type:** task · **Status:** completed · **Updated:** 2026-11-16 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-013-reinstall-pve-core-and-form-cluster.md)

**Authorization:** reinstalling `pve-core`, creating the cluster, joining nodes, quorum/QDevice changes,
API identities and OpenTofu applies are each operator-approved operations. A task status never
authorizes a live change by itself.

## Goal

`pve-core` (Ryzen 7 6800H, 8C/16T, 32 GB DDR5; emptied, workloads moved to `pve-lab`) becomes the
first node joined to the new cluster founded on `pve-management` ([ADR-010](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management)),
ready to host the runner (M003) and k3s (M004).

## Context

- Reuse the M001 pattern: read-only discovery (`scripts/pve-discover.py`), scoped token in Infisical,
  TLS CA in the workstation trust store, guarded Make targets
  ([INV-pve-management-bootstrap](/docs/investigations/pve-management-bootstrap)).
- Legacy roots `pve-core-tfstate` and `pve-core-garage` target `pve-core` (default `192.168.0.11`) and
  record guests that moved to `pve-lab` ([INV-legacy-inventory](/docs/investigations/legacy-inventory)).
  Extend `LEGACY_ENDPOINT_GUARD` to that address before the reinstall, as was done for `192.168.0.10`.
- Two-node cluster: losing either node blocks cluster writes; evaluate an external QDevice. Joining
  creates no shared storage ([ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups)).
- `pve-management` has 15.3 GiB RAM, 10 GiB of it for VM 100: new workloads go to `pve-core`.

**Outcome (2026-11-16):** the operator installed Proxmox VE 9.2 on `pve-core` (.11), a new `pve-infra`
(.12) and a new `pve-lab` (.16) and joined them, with `pve-management`, into cluster `doku-lab`. Facts:
[INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory).

## Acceptance criteria

- [x] Operator confirms `pve-core` has no workload or data to keep; disk/NVMe layout recorded (inventory)
- [x] Legacy endpoint guard covers the `pve-core` address (and .12, .16); guard tested in a sandbox
- [x] Proxmox VE installed cleanly; the cluster shares one root CA (trusted on the workstation) and the existing token sees all nodes
- [x] Cluster created on `pve-management`, nodes joined; VM 100 kept running throughout
- [x] Quorum: four voting nodes, quorum 3, one node may fail; no QDevice needed (recorded)
- [ ] Repeatable install-and-join procedure: deferred to the next reclaimed host (`pve-compute`, M010/M011); the joins were manual

## Verification

```
make mgmt-check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/mgmt-control.py` | Make guards (extend for the `pve-core` address) | `.venv/bin/python tests/mgmt-control.py` | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Cluster membership and quorum | `doku-lab`, 4/4 nodes, quorate, expected votes 4 | `pvecm status` on all nodes | 2026-11-16 |
| Hardware, storage, network, guests | Recorded; only VM 100 exists | INV-new-proxmox-cluster-inventory | 2026-11-16 |
| Legacy guard (.10/.11/.12/.16) | PASS | tests/mgmt-control.py | 2026-11-16 |

## Completion summary

Completed 2026-11-16 by the operator's manual installs and joins, verified read-only.
