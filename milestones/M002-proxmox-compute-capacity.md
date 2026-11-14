---
id: M002
title: "New Proxmox compute capacity (pve-core, new cluster)"
summary: "pve-core is reinstalled cleanly and joined to the new Proxmox cluster founded on pve-management, with the two-node quorum handled explicitly."
type: milestone
status: planned
priority: critical
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: [TASK-013]
related_decisions: [ADR-010, ADR-001]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M001]
completion_criteria: []
---

# M002 — New Proxmox compute capacity (pve-core, new cluster)

## Objective

Turn the emptied `pve-core` (Ryzen 7 6800H, 8C/16T, 32 GB DDR5) into the first compute node of the new cluster without disturbing `pve-management`, `mgmt-control-01` or `pve-lab`.

**Completion criterion:** pve-core is reinstalled cleanly and joined to the new Proxmox cluster founded on pve-management, with the two-node quorum handled explicitly.

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

- [ ] `pve-core` reinstalled and joined; `pve-management` and VM 100 unaffected
- [ ] Quorum behaviour with two nodes documented and the chosen mitigation applied
- [ ] NVMe devices and free capacity of both hosts recorded

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
