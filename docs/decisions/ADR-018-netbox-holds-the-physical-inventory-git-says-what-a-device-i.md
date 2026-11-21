---
id: ADR-018
title: "NetBox holds the physical inventory: Git says what a device is, machines report their hardware, people place it"
summary: Device identity comes from inventory.yaml, hardware and cabling from what hosts and the switch report, placement stays with people in NetBox; diagram plugins are installed on a volume.
type: decision
status: accepted
importance: 3
created: 2026-11-21
updated: 2026-11-21
tags: [netbox, inventory, hardware]
component: netbox
related: [ARCH-platform, DOC-infrastructure-inventory]
related_tasks: [TASK-030, TASK-023]
related_milestones: [M013]
supersedes: []
superseded_by: []
---

# NetBox holds the physical inventory: Git says what a device is, machines report their hardware, people place it

## Context

[ADR-016](ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md) made NetBox the inventory
and left physical devices to it: the reconciliation created them once from a seed and never touched them
again. Two days later the result was thin and partly wrong (an "Unknown" type on four devices, a backup
server recorded as a device although it is a VM), and nothing could correct it but a person clicking. The
operator asked on 2026-11-20 for NetBox to be the source of truth for deployment, documentation and
reference, with diagrams. M013 had excluded plugins, racks and cabling "until a person records them".

## Decision

- **Three owners per device, by field.** `services/netbox/inventory.yaml` owns what a device is: name, type,
  role, platform, cluster, status, description, ports, addresses. The machines own what they can report:
  serial number, processor, memory, disks, hardware addresses, link speed, and the switch port a host is
  plugged into (the switch announces it, the host only listens). People own the rest in NetBox: rack,
  position, asset tag, comments, contacts, extra tags. A rack or position stated in the file is written only
  while NetBox has none.
- **Serial numbers and hardware addresses go to NetBox only**: never to Git, never to the output of a plan.
- **Guests of the old environment** are described in the file by VMID or range; a described guest gets its
  role and loses the review flag. Proxmox keeps deciding state, size, disks and host of every guest.
- **Deleting stays apart.** Plan and apply never delete. Records the file lists under `retired` are removed
  by `make netbox-prune`, one named record at a time, with a ten-minute superuser token; NetBox refuses when
  something still refers to the record.
- **Plugins are installed on a volume, not into an image**: pinned files with their checksums, installed once
  per release by an init container of the same NetBox image, read by the web and worker containers.
- **The inventory page of the documentation is generated from NetBox** and committed, so the wiki shows it
  without CI holding a NetBox credential.

## Alternatives considered

- **Keep devices created once, edited by hand** — the state this replaces: nothing corrected a wrong seed.
- **Let the file own every field of a device** — a position dragged in the rack view would be undone at the
  next run; placement is exactly what people do better in NetBox.
- **A custom NetBox image with the plugins** (what netbox-docker documents) — needs a registry and a build
  for one image, and every pod start would depend on it. Revisit when the platform has a registry.
- **netbox-proxbox or a Proxmox sync plugin** — labelled experimental for 4.7 and needs its own backend; the
  existing reconciliation already reads Proxmox.
- **SNMP or a login on the switch for the cabling** — needs credentials on the switch; LLDP needs none.

## Consequences

- To change what a device is, change the file; a change of those fields in NetBox is overwritten.
- A new host needs `facts:` and one run of `make netbox-discover-hardware`; a host that moves to another
  port gets a line to review, not a silent change, because the old cable is never removed automatically.
- The first start after a plugin or NetBox version change needs PyPI; later starts do not. A plugin without
  a release for the next NetBox version blocks that upgrade (floorplan declares 4.7 only).
- What no machine can tell (rack, positions, cables of devices that do not announce themselves) still needs
  a person, once.
