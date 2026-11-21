---
title: Bursts of full-size frames are lost on the way into the Intel I219 hosts
description: pve-core and pve-management lose 3 to 5 % of back-to-back full-size frames they receive; TCP from faster hosts falls to 20-60 Mbit/s. Cause not fixed yet.
published: true
tags:
- known-issue
- open
- issue
- network
- proxmox
editor: markdown
date: '2026-11-21T00:00:00.000Z'
dateCreated: '2026-11-21T00:00:00.000Z'
---

# Bursts of full-size frames are lost on the way into the Intel I219 hosts

> **ID:** ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte · **Type:** known-issue · **Status:** open · **Updated:** 2026-11-21 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/issues/bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte.md)

## Description

Found on 2026-11-21 while copying guests from the old host: a transfer into `pve-core` ran at 3 to 6 MB/s.
The sender and its cable were not the cause. `pve-core` (192.168.0.11) and `pve-management` (192.168.0.10),
the two hosts with an Intel I219-LM port (driver `e1000e`, 1 Gbit/s on the switch's RJ45 ports 8 and 5), lose
part of what they **receive** when full-size frames arrive back to back. What they send arrives intact.

Measured with raw TCP (8 s, idle network, the sender's own retransmission count) and with numbered UDP bursts:

| From → to | TCP | Retransmitted |
|---|---|---|
| old host (10 Gbit/s) → new `pve-lab` (2.5 Gbit/s) | 2356 Mbit/s | 0 % |
| old host → `pve-core` | 20 Mbit/s | 9.4 % |
| old host → `pve-management` | 29 Mbit/s | 6.7 % |
| new `pve-lab` → `pve-core` | 17 Mbit/s | 10.1 % |
| new `pve-lab` → `pve-infra` (1 Gbit/s, Realtek) | 934 Mbit/s | 0.06 % |
| `pve-infra` → `pve-core` | 181 Mbit/s | 2.7 % |
| `pve-management` → `pve-core` | 384 Mbit/s | 0.3 % |
| `pve-core` → any host | about 935 Mbit/s | 0 % |

- In a burst of 1400-byte datagrams the first frame always arrives, the second is lost 20 to 30 % of the time
  from a faster sender, and every later position loses 3 to 5 %, whatever the length of the burst: not a
  buffer that overflows.
- With 15 µs between frames, or with 200- and 600-byte frames, nothing is lost. A flood ping loses nothing.
- A capture on `nic0` of `pve-core` sees exactly the frames the application receives: the missing ones never
  reach the driver. The port counts no CRC error, no missed frame, no drop; the kernel counts none either.
- `pve-infra`, at the same speed on the same kind of switch port, receives the same bursts intact: the switch
  copes with the difference of speed.
- The driver's `disable-k1` flag (`ethtool --set-priv-flags nic0 disable-k1 on`) lowers the loss from about
  4.2 % to 3.0 % and the loss of the second frame from about 25 % to 10 %: the port's receive path is involved,
  but K1 is not the whole cause. Keeping the processors out of their sleep states changes nothing.

What is not known: whether the frames are dropped inside the I219 (between its PHY and MAC) or already by the
switch on those two ports. The switch's own counters for ports 5 and 8 would tell; nobody has signed in to
the switch from here.

## Impact

Everything received by guests and services on those two hosts from a faster or burstier sender: `storage-01`
and `pg-01` on `pve-core` (volumes and database of the k3s workloads on the other nodes), `k3s-server-02`, the
workstation VM and `ts-router-02` on `pve-management`, guest migrations and backups into either host.
Throughput collapses rather than connections failing, so nothing reports an error.

## Workaround

- Bulk copies into these hosts: several TCP connections in parallel (each is slowed independently). The guest
  copies of 2026-11-21 went from 5 to 45 MB/s over twelve SSH sessions.
- `disable-k1` is on at `pve-core` since 2026-11-21 (not persistent: a reboot or a link reset by the driver
  puts it back). It helps a little.

## Resolution plan

Open, the operator decides. In order of cost:

1. Read the switch's per-port counters (drops on ports 5 and 8) and try its port settings (flow control, energy
   saving); update the switch firmware.
2. On the hosts, with the operator's approval for each: the driver's large-frame receive settings (raising the
   MTU of `nic0` makes `e1000e` reconfigure the PHY's receive buffer and turn K1 off), then a newer kernel.
3. Another network port for the two hosts (a 2.5 Gbit/s Realtek adapter like the one in the new `pve-lab`,
   which receives 2.3 Gbit/s without loss).

Whatever works is then made permanent through Ansible and recorded here.
