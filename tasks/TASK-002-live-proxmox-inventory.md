---
id: TASK-002
title: "Live read-only inventory of Proxmox hosts, guests and storage"
summary: "Verify hosts, cluster membership, VMs/LXCs, storage and capacity on every node; correct the legacy inventory."
type: task
status: planned
priority: critical
milestone: M000
created: 2026-11-12
updated: 2026-11-12
tags: [inventory, proxmox]
depends_on: [TASK-001]
related: [ARCH-platform]
related_decisions: [ADR-007]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-002 — Live read-only inventory of Proxmox hosts, guests and storage

**Authorization:** LIVE_READ — operator confirms access method first. A task status never authorizes a live change by itself.

## Goal

Replace the unverified legacy inventory with observed facts.

## Context

- [INV-legacy-inventory](../docs/investigations/legacy-inventory.md), including the pve-infra / pve-management address discrepancy
- Legacy inventory `ansible/inventories/homelab.yml`
- `pve-management` facts needed for M001 are verified in TASK-007; this task covers the legacy estate

## Acceptance criteria

- [ ] Each Proxmox host listed with version, cluster membership, CPU/RAM/storage and free capacity
- [ ] Every VM/LXC listed with node, purpose, owner (IaC root or manual) and state
- [x] pve-infra/pve-compute confirmed retired by the operator; removed from the Ansible inventory and Prometheus targets
- [ ] Former pve-infra/pve-compute workloads located (CT301 runner host, DNS/proxy)
- [ ] No credential values or private configuration recorded

## Verification

- Read-only `pvesh`/`qm list`/`pct list`/`pvesm status` per node (commands recorded in the evidence table)

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| | not verified | | |

## Completion summary

_Not completed._
