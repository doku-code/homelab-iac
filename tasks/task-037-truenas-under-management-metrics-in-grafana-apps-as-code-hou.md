---
title: 'TASK-037 — TrueNAS under management: metrics in Grafana, apps as code, housekeeping'
description: The NAS's metrics and alerts in the monitoring stack, its apps described in the repository with a plan-before-apply path, and the leftovers of the old environment cleaned up
published: true
tags:
- task
- in-progress
- truenas
- monitoring
editor: markdown
date: '2026-11-27T00:00:00.000Z'
dateCreated: '2026-11-27T00:00:00.000Z'
---

# TASK-037 — TrueNAS under management: metrics in Grafana, apps as code, housekeeping

> **ID:** TASK-037 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-27 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-037-truenas-under-management-metrics-in-grafana-apps-as-code-hou.md)

## Goal

The NAS (TrueNAS 25.10, 192.168.0.13) was outside the repository until 2026-11-26. The operator asked to manage it
like the rest: its metrics and alerts in the monitoring stack, its apps described in the repository with a
plan-before-apply path, and the leftovers of the old environment cleaned up. The apps stay on the NAS.
Pools, datasets, permissions and existing shares change only with the operator's word.

Access: user `homelab-iac` (Full Admin), API key in the store path `/truenas`; interface and API on HTTPS port 444.
The key must never travel over plain HTTP: TrueNAS revokes it.

## Acceptance criteria

- [x] Metrics of the NAS in VictoriaMetrics, a Grafana dashboard and alert rules (pools, disks, apps, silence).
- [x] Apps described in the repository with a plan and an approval-gated apply (`qbit-vpn`, `plex`).
- [x] `qbit-vpn` runs the pinned digests.
- [x] Homepage reads the NAS without the deprecated REST API.
- [x] Timezone America/Toronto.
- [ ] bond0 replaced by its SFP+ member (two attempts rolled back, see Evidence).

## Evidence

| Date | What | Result |
|---|---|---|
| 2026-11-27 | Read-only inventory through the API | 25.10.7; pools tank, fastpool, apps-pool healthy, pve-pool offline (dead disk, to ignore); apps qbit-vpn, plex, nextcloud, forgejo running; no snapshot task, replication or cloud sync |
| 2026-11-27 | Timezone | `America/Toronto` read back |
| 2026-11-27 | Metrics exporter of the NAS repointed from 192.168.0.28 (gone) to 192.168.0.45:9109 | Graphite lines arrive; port closed for other sources |
| 2026-11-27 | `truenas-exporter.py` run against the NAS | pools, datasets, 3 disk temperatures, 4 apps, alerts by level, over the WebSocket API |
| 2026-11-27 | `make observability-check` | PASS |
| 2026-11-27 | Dashboard and rules live | Grafana lists `TrueNAS` (19 panels); 7 rules loaded, all inactive; per-disk activity joined with device names |
| 2026-11-27 | `truenas-apps.py export` of `qbit-vpn` and `plex`, then `make truenas-plan` | both "no change"; the VPN key went to the store, not the file |
| 2026-11-27 | `qbit-vpn` images pinned to the running digests, `make truenas-plan` | 2 to change (image references only); apply not run |
| 2026-11-27 | `make truenas-check` | PASS |
| 2026-11-27 | bond0 removal, twice, with TrueNAS's rollback | NAS unreachable once the address is on enp1s0 alone; rolled back by itself both times (about 1.5 and 4 minutes of outage). Not the hardware address: the bond already uses enp1s0's. Not retried blind |
| 2026-11-27 | `make truenas-apply TRUENAS_APPS=qbit-vpn` (operator's go, on condition that the download list stays) | refused twice by TrueNAS at validation ("Invalid compose configuration: Timed out waiting for response", the NAS was busy), accepted the third time (about 3 minutes); plan "no change"; 8 torrents in qBittorrent's state directory before and after, 8 through its API |
| 2026-11-27 | Homepage's NAS card from VictoriaMetrics (`truenas_*`), no NAS key in its Secret | snapshot shows 4 pools, 4 apps, load, uptime, version; the NAS's audit log has no session of the key `homepage-metrics` in the 5 minutes after the old pod ended (30 per 5 minutes before) |
| 2026-11-27 | Homepage's qBittorrent card | qBittorrent 5.3 answers a login with 204 and no body; the card accepted only `Ok.` and showed an error. Fixed; card online (1 downloading, 6 seeding) |
| 2026-11-27 | `make homepage-k3s-check` | PASS |

## Completion summary

Remaining: describe `nextcloud`, the bond, the unused API key `homepage-metrics` on the NAS (the operator's to delete or to approve)
(from the NAS console, or by removing only enp3s0 from it), then the media stack's use of the NAS (TASK-036).
