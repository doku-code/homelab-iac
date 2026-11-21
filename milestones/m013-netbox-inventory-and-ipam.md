---
title: M013 — NetBox inventory and IPAM
description: NetBox runs on k3s as the inventory and IPAM source of truth, is populated from OpenTofu outputs and read-only Proxmox discovery, and Ansible can read its inventory from it.
published: true
tags:
- milestone
- active
- roadmap
- netbox
- inventory
editor: markdown
date: '2026-11-21T00:00:00.000Z'
dateCreated: '2026-11-18T00:00:00.000Z'
---

# M013 — NetBox inventory and IPAM

> **ID:** M013 · **Type:** milestone · **Status:** active · **Updated:** 2026-11-21 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M013-netbox-inventory-and-ipam.md)

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
- Since 2026-11-20 (operator's request, ADR-018): real hardware models, ports, hardware facts read from the
  hosts, cabling, racks, and plugins that draw the network and the room.

Out of scope:

- Kubernetes workloads as inventory records; credentials in NetBox.
- NetBox as a prerequisite of any root's plan or apply.
- Anything no machine reports and no person stated: nothing is invented.

## Expected deliverables

- `services/netbox/`, `scripts/netbox-sync.py`, `ansible/inventories/netbox.yml`, Make targets `netbox-*`.
- [ADR-016](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f).

## Dependencies

- k3s (M004), shared storage (M006), shared PostgreSQL (M007); DNS and certificates from TASK-022.

## Acceptance criteria

- [x] NetBox deployed from the repository, LAN only, login required, credentials in the secret store
- [x] Initial inventory from Git and discovery, reconciliation repeatable and non-destructive
- [x] Ansible reads the inventory of the Git-defined VMs from NetBox
- [ ] Every record tagged `needs-review` validated by the operator
- [x] Each root's plan checks its addresses and VMIDs against NetBox (and still works without it)
- [x] Named hardware models, ports, host hardware and the cables the switch announces; topology and floor plan plugins
- [ ] Rack, positions and the cables no machine announces, from the operator's facts
- [x] A second consumer (Windmill form, Prometheus targets or the deployment runner) reads from NetBox

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Deployment, inventory, Ansible inventory | See [TASK-023](/tasks/task-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i) | Done: NetBox 4.7.5 running, 165 records created, second plan empty, 10 hosts identical to the OpenTofu inventories | 2026-11-18 |
| Records validated | NetBox, tag `needs-review` | not verified: 7 records left of 34 (pfSense, access point, old host, three stopped containers, the DHCP range); see [TASK-030](/tasks/task-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues) | 2026-11-20 |
| Second consumer | Windmill scripts `f/netbox/*` run inside Windmill against the NetBox API ([TASK-025](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox)) | Done | 2026-11-18 |
| Allocation check in the roots | `make dns-plan`, `make k3s-cluster-plan` | Done: `allocation: 1 machine(s) of the plan agree with NetBox`, `3 machine(s)`; passes with a notice when NetBox or the store does not answer (TASK-030) | 2026-11-21 |
| Hardware, cabling, plugins | `make netbox-apply`, `/api/status/` | Done: 9 named device types, 47 ports, 4 cables from LLDP, 14 inventory items, three plugins loaded (TASK-030) | 2026-11-21 |
| Rack and remaining cables | | not verified: waits for the operator's facts | |

## Completion summary

Active. Foundation (TASK-023), full hardware inventory, diagrams and the plan check (TASK-030) are in place.
Remaining: the operator's facts about the rack and the cables no machine announces, the seven records still
flagged, and the scheduled export to a private Forgejo repository.
