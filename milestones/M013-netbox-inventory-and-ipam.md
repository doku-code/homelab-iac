---
id: M013
title: NetBox inventory and IPAM
summary: NetBox runs on k3s as the inventory and IPAM source of truth, is populated from OpenTofu outputs and read-only Proxmox discovery, and Ansible can read its inventory from it.
type: milestone
status: active
priority: medium
created: 2026-11-18
updated: 2026-11-18
tags: [roadmap, netbox, inventory]
related_tasks: [TASK-023]
related_decisions: [ADR-016, ADR-015, ADR-012, ADR-011]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M004, M006, M007]
completion_criteria: []
---

# M013 — NetBox inventory and IPAM

## Objective

One place lists every machine, its host, its addresses and whether a person verified it, and automation
reads from it instead of repeating host facts, without NetBox becoming something the platform needs in
order to be rebuilt.

**Completion criterion:** NetBox holds a validated inventory (no record left `needs-review`), the roots
check their addresses and VMIDs against it before an apply, and at least one consumer besides Ansible
reads from it.

## Scope

In scope:

- NetBox on k3s from this repository, on the shared PostgreSQL and the shared NVMe storage.
- Inventory of Proxmox hosts, VMs and containers, prefix, ranges and addresses, from Git and read-only
  discovery, with a repeatable reconciliation.
- Ansible inventory from NetBox; an allocation check for the OpenTofu roots.

Out of scope:

- Kubernetes workloads as inventory records; credentials in NetBox; NetBox plugins.
- NetBox as a prerequisite of any root's plan or apply.
- Racks, cabling and VLANs until a person records them: nothing is invented.

## Expected deliverables

- `services/netbox/`, `scripts/netbox-sync.py`, `ansible/inventories/netbox.yml`, Make targets `netbox-*`.
- [ADR-016](../docs/decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md).

## Dependencies

- k3s (M004), shared storage (M006), shared PostgreSQL (M007); DNS and certificates from TASK-022.

## Acceptance criteria

- [x] NetBox deployed from the repository, LAN only, login required, credentials in the secret store
- [x] Initial inventory from Git and discovery, reconciliation repeatable and non-destructive
- [x] Ansible reads the inventory of the Git-defined VMs from NetBox
- [ ] Every record tagged `needs-review` validated by the operator
- [ ] Each root's plan checks its addresses and VMIDs against NetBox (and still works without it)
- [ ] A second consumer (Windmill form, Prometheus targets or the deployment runner) reads from NetBox

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Deployment, inventory, Ansible inventory | See [TASK-023](../tasks/TASK-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i.md) | Done: NetBox 4.7.5 running, 165 records created, second plan empty, 10 hosts identical to the OpenTofu inventories | 2026-11-18 |
| Records validated | NetBox, tag `needs-review` | not verified: 34 records wait for the operator | |
| Allocation check, second consumer | | not started | |

## Completion summary

Active. The foundation is in place (TASK-023). Remaining: the operator's review of the flagged records, the
allocation check in the roots' plan targets, a second consumer.
