---
id: TASK-013
title: Reinstall pve-core and form the new Proxmox cluster
summary: "Confirm the emptied pve-core holds nothing to keep, inventory its NVMe, reinstall Proxmox VE, create the cluster on pve-management and join pve-core with an explicit two-node quorum plan."
type: task
status: planned
priority: critical
milestone: M002
created: 2026-11-14
updated: 2026-11-14
tags: [compute, proxmox, cluster, pve-core, m002]
depends_on: [TASK-009]
related: [GUIDE-handoff, ARCH-platform, INV-legacy-inventory, INV-pve-management-bootstrap]
related_decisions: [ADR-010, ADR-001, ADR-003, ADR-012]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-013 — Reinstall pve-core and form the new Proxmox cluster

**Authorization:** reinstalling `pve-core`, creating the cluster, joining nodes, quorum/QDevice changes,
API identities and OpenTofu applies are each operator-approved operations. A task status never
authorizes a live change by itself.

## Goal

`pve-core` (Ryzen 7 6800H, 8C/16T, 32 GB DDR5; emptied, workloads moved to `pve-lab`) becomes the
first node joined to the new cluster founded on `pve-management` ([ADR-010](../docs/decisions/ADR-010-new-proxmox-cluster-on-pve-management.md)),
ready to host the runner (M003) and k3s (M004).

## Context

- Reuse the M001 pattern: read-only discovery (`scripts/pve-discover.py`), scoped token in Infisical,
  TLS CA in the workstation trust store, guarded Make targets
  ([INV-pve-management-bootstrap](../docs/investigations/pve-management-bootstrap.md)).
- Legacy roots `pve-core-tfstate` and `pve-core-garage` target `pve-core` (default `192.168.0.11`) and
  record guests that moved to `pve-lab` ([INV-legacy-inventory](../docs/investigations/legacy-inventory.md)).
  Extend `LEGACY_ENDPOINT_GUARD` to that address before the reinstall, as was done for `192.168.0.10`.
- Two-node cluster: losing either node blocks cluster writes; evaluate an external QDevice. Joining
  creates no shared storage ([ADR-012](../docs/decisions/ADR-012-external-nvme-storage-truenas-backups.md)).
- `pve-management` has 15.3 GiB RAM, 10 GiB of it for VM 100: new workloads go to `pve-core`.

## Acceptance criteria

- [ ] Operator confirms `pve-core` has no workload or data to keep; disk/NVMe layout recorded (model, size, partitions)
- [ ] Legacy endpoint guard covers the `pve-core` address; guard tested in a sandbox
- [ ] Proxmox VE installed cleanly; root CA trusted on the workstation; scoped token stored in Infisical; discovery passes
- [ ] Cluster created on `pve-management`, `pve-core` joined; VM 100 keeps running throughout
- [ ] Quorum mitigation chosen (QDevice or documented acceptance) and recorded
- [ ] Repeatable install-and-join procedure documented for the next reclaimed host

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
| | not verified | | |

## Completion summary

_Not completed._
