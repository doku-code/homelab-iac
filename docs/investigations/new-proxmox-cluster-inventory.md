---
title: New Proxmox cluster inventory
description: 'Authoritative read-only audit of the new doku-lab cluster (pve-management, pve-core, pve-infra, new pve-lab .16): membership, hardware, NVMe, network, guests, capacity, placement.'
published: true
tags:
- investigation
- current
- inventory
- proxmox
- cluster
- hardware
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-16T00:00:00.000Z'
---

# New Proxmox cluster inventory

> **ID:** INV-new-proxmox-cluster-inventory · **Type:** investigation · **Status:** current · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/investigations/new-proxmox-cluster-inventory.md)

Authoritative inventory of the **new** Proxmox environment. The old, independent environment is in
[INV-legacy-inventory](/docs/investigations/legacy-inventory). Update this page when hardware or membership changes.

## Question

What does the new cluster actually contain (membership, health, hardware, storage, network, guests), and
where can the next workloads (runner, k3s, storage) go?

## Method

Read-only audit on 2026-11-16 from `mgmt-control-01` over root SSH (the workstation key
`keys/mgmt-control-01.pub`, authorized cluster-wide in `/etc/pve/priv/authorized_keys` by the operator),
plus the Proxmox API token. Commands: `pvecm status`, `/etc/pve/corosync.conf`, `pveversion`, `lscpu`,
`dmidecode`, `lsblk`, `/dev/disk/by-id`, `pvesm status`, `vgs/lvs`, `zpool list`, `lspci`, `ethtool`,
`/etc/network/interfaces`, `timedatectl`/`chronyc`, `qm list`/`pct list`, `getent hosts`, `ping`. Nothing
was changed. Host keys were checked against the cluster's own records (`/etc/pve/nodes/*/ssh_known_hosts`).
Raw output (with disk serials and MAC addresses): `.local/audit/2026-11-16/` on the workstation.

## Findings

### Cluster (verified)

| Item | Value |
|------|-------|
| Name | `doku-lab`, config version 4, knet transport, secure auth on |
| Members | 4 of 4 online: `pve-management` (id 1, .10), `pve-core` (2, .11), `pve-infra` (3, .12), `pve-lab` (4, .16) |
| Quorum | Quorate, expected votes 4, quorum 3: tolerates **one** node down. No QDevice needed |
| Corosync links | One link (`link0`) on the management LAN 192.168.0.0/24, shared with guest traffic; no redundant link |
| HA | Not configured (`ha-manager`: quorum OK, fencing standby) |
| Proxmox VE | 9.2.28 on all nodes |
| Kernel | 7.0.14-29-pve on .11/.12/.16; **7.0.14-28-pve on pve-management** (one update behind, needs a reboot to match) |
| Time | NTP active and synchronized on all nodes (chrony, sub-millisecond offset), time zone America/Toronto |
| Old host | `192.168.0.14` (old `pve-lab`) is **not** a member, as intended |

### Hosts (verified)

| Node | IP | Machine | CPU (cores/threads) | RAM | Boot/data disk | NIC (negotiated) |
|------|----|---------|---------------------|-----|----------------|------------------|
| `pve-management` | 192.168.0.10 | Lenovo ThinkCentre M90q Tiny | Intel i5-10500T, 6C/12T, VT-x | 16 GB DDR4-2666 (1 DIMM) | KIOXIA BG6 256 GB NVMe (DRAM-less) | Intel I219-LM, e1000e, **1 GbE** |
| `pve-core` | 192.168.0.11 | Lenovo ThinkStation P350 Tiny | Intel i7-11700, 8C/16T, VT-x | 32 GB DDR4-3200 (2×16) | Kingston NV1 1 TB NVMe (DRAM-less) | Intel I219-LM, e1000e, **1 GbE** (+ unused Wi-Fi) |
| `pve-infra` | 192.168.0.12 | AZW MINI S | Intel Celeron **N5095A**, 4C/4T, VT-x | 8 GB DDR4-2667 | NGFF 256 GB **SATA** M.2 SSD (no NVMe) | Realtek RTL8111, r8169, **1 GbE** (+ unused Wi-Fi) |
| `pve-lab` (new) | 192.168.0.16 | ORIGIMAGIC Nebula | AMD Ryzen 7 6800H, 8C/16T, AMD-V | 32 GB DDR5-4800 (2×16; 28 GiB visible, iGPU reserve) | Lexar NM610 PRO 512 GB NVMe (DRAM-less) | Realtek RTL8125, r8169, **2.5 GbE** (+ unused Wi-Fi) |

IOMMU is enabled on every node. Each node has **exactly one** SSD, holding the Proxmox install and its
storage. Stable disk IDs: `/dev/disk/by-id/nvme-eui.*` (NVMe) and `ata-*` (pve-infra), listed in the raw audit.

Differences from the operator's 2026-11-16 brief: `pve-infra` is a Celeron N5095A (not an Intel N95) with
a SATA SSD; `pve-management` is a ThinkCentre M90q with 16 GB. [ADR-010](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management)
described the emptied `pve-core` as the Ryzen 7 6800H; that CPU is now in the new `pve-lab`, and
`pve-core` is the P350 Tiny.

### Storage (verified)

Default Proxmox layout on every node: VG `pve` with `root`, `swap` and LVM-thin pool `data`; storages
`local` (dir: ISO, templates, backups, import) and `local-lvm` (lvmthin: VM/CT disks). No ZFS, no Ceph, no
shared storage, 16 GiB unallocated in each VG.

| Node | `local-lvm` thin pool | Used | `local` free |
|------|-----------------------|------|--------------|
| `pve-management` | 141 GiB | VM 100 disk (120 GiB thin, ~17 % written) | 50 GiB |
| `pve-core` | 849 GiB | empty | 31 GiB |
| `pve-infra` | 170 GiB (SATA) | empty | 31 GiB |
| `pve-lab` | 403 GiB | empty | 31 GiB |

The Ubuntu Desktop ISO exists only on `pve-management`'s `local`.

### Network (verified)

- One physical NIC per node in use, enslaved to `vmbr0` (no VLANs, MTU 1500), static IP on
  192.168.0.0/24, gateway 192.168.0.1, DNS 192.168.0.20 (AdGuard), search `doku-lab.net`.
- Negotiated speeds equal the NICs' maximum: 1 GbE on .10/.11/.12, 2.5 GbE on .16. **No 10/25 GbE
  hardware is installed yet.** Every node reaches the others, the gateway and AdGuard (< 1.5 ms).
- Name resolution: none of the four nodes has a DNS record in AdGuard; each resolves only itself through
  `/etc/hosts`. `pve-lab.doku-lab.net` resolves to **192.168.0.24** (a proxy answering HTTPS, in front of the
  old environment), never to the new `.16`. **Address the new cluster by IP** in automation.

### Guests (verified)

Only VM 100 `mgmt-control-01` (running, 10 GiB, 120 GiB) on `pve-management`. No other VM or container
on any node.

## Inferences

### Capacity

| Node | Free for guests (approx.) | Suited for |
|------|---------------------------|------------|
| `pve-management` | ~1–2 vCPU, ~4 GiB, ~20 GiB thin | Nothing more: it hosts the workstation |
| `pve-core` | 16 threads, ~28 GiB, 849 GiB NVMe | k3s node; first external NVMe storage (largest disk) |
| `pve-lab` | 16 threads, ~24 GiB, 403 GiB NVMe | First k3s server (fastest CPU, DDR5, 2.5 GbE) |
| `pve-infra` | 4 threads, ~5 GiB, 170 GiB SATA | Dedicated Forgejo runner (M003), lightweight services, later a small etcd/k3s member |

Proposed placement (decided in each milestone, not allocated now): runner VM on `pve-infra` (M003; the
operator decided `pve-core` with 6 vCPU / 8 GiB on 2026-11-17, TASK-014);
first k3s server on `pve-lab`, then a second node on `pve-core`, a third etcd voter later (M004);
storage on `pve-core` first (M006). No physical HA is claimed: every node has one SSD, one NIC and one
corosync link.

### Storage options for M006 (input, not a decision)

No node has a spare NVMe device, so Ceph OSDs (M011) need new disks or reclaimed hosts first. Realistic
first steps that keep data outside k3s VM disks, on the physical NVMe:

1. **Proxmox CSI plugin** over each node's `local-lvm`: PVs are Proxmox volumes attached to the k3s VMs,
   node-local (zone-bound), later backed by Ceph RBD with the same driver. No extra storage VM.
2. **Storage VM on `pve-core`** (ZFS or LVM inside) exported to k3s through democratic-csi (NFS/iSCSI):
   one failure domain, shared volumes possible.

PostgreSQL/Patroni (M007) replicates at the database layer, which suits node-local volumes.

## Open questions

- Upgrade `pve-management`'s kernel/reboot to match the other nodes (operator-approved maintenance).
- A second corosync link and 10/25 GbE NICs arrive with the network upgrade (M011).
- DNS records for the new nodes (unambiguous names) are a networking change for the operator.
