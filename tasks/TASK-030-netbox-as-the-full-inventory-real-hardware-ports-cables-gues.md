---
id: TASK-030
title: "NetBox as the full inventory: real hardware, ports, cables, guests and diagram plugins"
summary: NetBox holds named hardware models, ports, hardware facts, the cables the switch announces and what every guest is, draws diagrams through plugins, and the roots check their plans against it.
type: task
status: in-progress
priority: medium
milestone: M013
created: 2026-11-20
updated: 2026-11-22
tags: [netbox, inventory, hardware]
depends_on: [TASK-023]
related: [ARCH-platform, DOC-infrastructure-inventory, REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll]
related_decisions: [ADR-018, ADR-016, ADR-012]
related_implementations:
  - services/netbox/inventory.yaml
  - services/netbox/values.yaml
  - services/netbox/access.yaml
  - scripts/netbox-sync.py
  - scripts/host-facts.py
  - docs/reference/infrastructure-inventory.md
  - Makefile
related_tests:
  - tests/netbox.py
tests_justification: ""
verification_commands:
  - make netbox-check
  - scripts/secrets.py run /netbox -- make netbox-plan
evidence: []
---

# NetBox as the full inventory: real hardware, ports, cables, guests and diagram plugins

## Goal

The operator's request of 2026-11-20: NetBox is the source of truth for deployment, documentation and
reference. It was sparse (four devices of an "Unknown" type, no ports but a bridge, no cable, 34 records
waiting for a review) and had no diagram. It should hold the real hardware and show it.

## Context

- [ADR-016](../docs/decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md) keeps
  applying; [ADR-018](../docs/decisions/ADR-018-netbox-holds-the-physical-inventory-git-says-what-a-device-i.md)
  records what changed: who owns which field of a device, and how plugins are installed.
- What could be read without asking anyone was read on 2026-11-20: the four Proxmox hosts of doku-lab report
  their own hardware (`scripts/host-facts.py`), and hear the switch announce its name, address and the port
  they are plugged into (LLDP); the access point shows its model on its sign-in page; TrueNAS answers its
  API with the dashboard's read key; the old host answers the Proxmox API. pfSense is never signed in to.

## What was built

- `services/netbox/inventory.yaml`: device types with their ports (no "Unknown" left), the switch (QNAP
  QSW-M3216R-8S8T, found by LLDP at 192.168.0.116) and the access point as devices, bridges, aggregates and
  the management engine of pve-core as ports, addresses on ports, the backup server as a VM on TrueNAS, the
  k3s and Tailscale networks, what each guest of the old environment is, optional racks and stated cables,
  and a list of retired records.
- `scripts/host-facts.py` and `make netbox-discover-hardware`: read-only hardware facts of a host over SSH
  (model, serial number, processor, memory modules, disks, ports, hardware addresses, link speed, LLDP
  neighbour). Serial numbers and hardware addresses go to NetBox only: never to Git, never to the output.
- `scripts/netbox-sync.py`: fields written always, fields written only while NetBox has none (rack, position),
  a flag removed once a record is described; interface templates, hardware addresses, inventory items,
  virtual disks, cables (LLDP: tag `observed`), services on devices; `prune` (removes only what the file
  retires, with a ten-minute superuser token), `icons` (pictures of the roles in the diagram), `check-plan`
  and `document`.
- Plugins: netbox-topology-views 5.0.2, netbox-floorplan-plugin 0.10.0, netbox-reorder-rack 1.1.5, pinned by
  checksum and installed once per release on the volume `netbox-plugins` by an init container.
- The six roots that create VMs run `check-plan` after saving their plan: a VMID or an address NetBox gives
  to another machine stops the target before the checksum is printed; without NetBox the check says so and
  passes.
- `docs/reference/infrastructure-inventory.md`, rewritten from NetBox by `make netbox-docs` and shown by the wiki.

## Acceptance criteria

- [x] Every device has a named type with its ports; nothing is called unknown
- [x] The Proxmox hosts report their hardware; serial numbers and hardware addresses never reach Git or the output
- [x] Cables between the hosts and the switch are recorded from what the switch announces
- [x] Every guest of the old environment has a role and a description; the review flag stays only where nobody verified
- [x] A second plan after an apply changes nothing; nothing is deleted outside the retired list
- [x] Topology and floor plan plugins run, pinned by checksum, without a custom image
- [x] Each root's plan checks its VMIDs and addresses against NetBox and still works without it
- [x] The inventory is a page of the documentation, generated from NetBox
- [x] The rack, pfSense's hardware and the switch's port layout as the operator stated them (2026-11-21)
- [ ] Positions in the rack, and the cables no machine announces (NAS, pfSense, access point, old host): wait for the operator

## Verification

```
make netbox-check
scripts/secrets.py run /netbox -- make netbox-plan
scripts/secrets.py run /netbox -- make netbox-docs
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/netbox.py | Reconciliation against an in-memory NetBox: types and numbered ports, bridge, aggregate and parent ports, hardware addresses, serial and inventory items from host facts, cable from LLDP (kept when a port is replugged, reported), described guests lose the flag, people's fields survive, rack written once, stated cable, virtual disks, second run empty, nothing printed that is private; `prune` removes only retired records and reports a refusal; allocation check (conflicts, free, no token, every root calls it before the checksum); LLDP decoding and read-only host script; plugins pinned by checksum, init container of the same image, release name; generated page without serials or personal names | `make netbox-check` | PASS 2026-11-21 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Hardware read | Four hosts: model, processor, memory, disks, ports; each hears `QSW-M3216R-8S8T` at 192.168.0.116 on ports 5 (pve-management), 6 (pve-lab), 7 (pve-infra), 8 (pve-core) | `make netbox-discover-hardware`, `.local/netbox/hardware-*.json` | 2026-11-20 |
| Plan and apply | `plan: 230 to create, 58 to update, nothing deleted`; `applied: 227 to create, 62 to update, nothing deleted` | `.local/netbox/plan-5.txt`, `apply-5.txt`; commit 9b2c736 | 2026-11-20 |
| Retired records | Seven removed (device `pbs`, three device types, three manufacturers), none refused | `make netbox-prune` | 2026-11-20 |
| Second plan | `plan: 0 to create, 0 to update, nothing deleted`; one line to review (the stopped AdGuard container still carries 192.168.0.20) | `make netbox-plan` | 2026-11-20 |
| Content | 9 device types, 9 devices (none unknown), 47 ports, 4 cables, 14 inventory items, 45 hardware addresses, 42 virtual disks, 4 prefixes, 17 services; flagged for review: 7 records (was 34) | NetBox API | 2026-11-20 |
| Plugins | Init container: `plugins v4.7.5-d787f1278b51: installed`; `/api/status/` lists the three plugins; web and worker rolled out, Argo CD `Synced Healthy`; the topology page draws the switch with its four hosts | commit 8c4363f; screenshot (not kept in Git) | 2026-11-21 |
| Allocation check | `allocation: 1 machine(s) of the plan agree with NetBox` (dns), `3 machine(s)` (k3s); both plans `No changes` | `make dns-plan`, `make k3s-cluster-plan`; commit fa268e6 | 2026-11-21 |
| Inventory page | `docs/reference/infrastructure-inventory.md: rewritten from NetBox`; 11 personal machines counted, not named | `make netbox-docs` | 2026-11-21 |
| Operator's facts | Rack `rack-01` (27 U, 19 inches, 610 mm deep; the switch in it, no position yet), pfSense on a Lenovo ThinkCentre M75q Gen 2 (WAN 1 Gb, LAN 2.5 Gb), switch ports 1 to 8 RJ45 and 9 to 16 SFP+, access point confirmed; `plan: 4 to create, 7 to update`, then an empty plan | `make netbox-apply`; commit 10ee98c | 2026-11-21 |
| Deleted guests | Nine replaced guests deleted from the old host by the operator's decision (`destroyed CT 200 adguard` … `destroyed VM 305 k3s-server-3`); their nine records removed from NetBox with their addresses; `plan: 0 to create, 0 to update`, no line to review | `.local/legacy-destroy-2026-11-21.log`, `make netbox-prune` | 2026-11-21 |
| Moved guests, tunnel, radios | `applied: 26 to create, 8 to update, nothing deleted`, second plan `0 to create, 0 to update`, no review line: the two Tailscale routers and two Windows VMs on doku-lab, tunnel `tailscale-lan` with both routers (port `tailscale0`, tailnet address, LAN address as the outside), radios `wlan0`/`wlan1` of the access point as access-point radios, uplink as PoE-powered; old router records removed (`removed … 'cluster': 'homelab'`) | `make netbox-discover-tailscale`, `make netbox-prune`, `make netbox-apply`, `make netbox-check` | 2026-11-21 |
| Wi-Fi networks | not verified: the mechanism exists (`.local/netbox/private.yaml`, tested offline) but no network name is known yet | | |
| Positions, remaining cables | not verified: nothing can read them | | |

## Not done

- Positions in the rack and the floor plan: the rack exists with the switch in it, unplaced. Where each
  device sits is the operator's to drag in NetBox (or `position` on the device in `inventory.yaml`); which
  of the small machines are in the rack at all was not stated.
- Cables of the NAS (10 Gb SFP+), pfSense, the access point and the old host: no machine announces them here.
  They go under `cables` in `inventory.yaml`.
- Setting 192.168.0.3 on the switch (the address the operator means for it, and where `switch.doku-lab.net`
  points): needs a login on the switch, which automation does not have. It answers at its DHCP lease
  192.168.0.116 until then.
- The exact model of the rack: "Sysracks SRW 27.600" fits the operator's description (27 U, 24 inches deep,
  "SRW something"); the label was not read.
- Applications on k3s are not NetBox records (Git and Argo CD own them, ADR-016).
- The scheduled export to a private repository (ADR-016) is still open.

## Completion summary

In progress. Everything a machine could tell and what the operator stated on 2026-11-21 is in NetBox, with
diagrams, the plan check and the generated page; since the same day also the Tailscale tunnel with its two
routers (now on doku-lab) and the access point's radios; since 2026-11-22 the switch at 192.168.0.3 and the cables
of pfSense (port 1), the old host (port 14) and the NAS (port 16), found by sending traffic and reading the
switch's port counters. Remaining: what sits between port 3 and the access point (that link runs at 2.5 Gbit/s),
the names of the Wi-Fi networks (the
operator gives them; they go to `.local/netbox/private.yaml`, never to Git), where the devices sit in the rack
(in NetBox, or `position` in `services/netbox/inventory.yaml`), then `make netbox-apply` and `make netbox-docs`. Not modelled yet and worth deciding with the
operator: the web applications behind the ingress as services, power (a UPS or power strip, if any), the
internet line as a circuit.
