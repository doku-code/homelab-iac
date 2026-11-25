---
title: Operations
description: 'Day-to-day procedures: where the commands are, how to take a host down, what is known to be broken.'
published: true
tags:
- guide
- current
- map
- operations
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Operations

> **ID:** GUIDE-map-operations · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/operations.md)

The commands in use and the current state are in the [handoff](/docs/handoff) ("Commands", "Infrastructure now").

## Routine

| Need | How |
|---|---|
| State of the project | `.venv/bin/harness status` |
| State of the cluster | <https://headlamp.doku-lab.net>, <https://argocd.doku-lab.net>, <https://grafana.doku-lab.net> |
| Change a service on k3s | Edit `services/<name>/`, merge to `main`; Argo CD applies it ([deployment map](/docs/hubs/deployment-map)) |
| Change a LAN name | Edit `ansible/vars/dns.yml`, then `scripts/secrets.py run /dns -- make dns-configure DNS_CONFIGURE_APPROVED=yes` |
| Bring NetBox up to date now | `scripts/secrets.py run /pve-management /netbox -- make netbox-autosync NETBOX_AUTOSYNC_APPROVED=yes` (a timer does it every 15 minutes) |
| Refresh the inventory page and these maps | `scripts/secrets.py run /netbox -- make netbox-docs`, then commit |
| Check single sign-on | `scripts/secrets.py run /authentik -- make sso-check` |

## Taking a Proxmox host down

1. Park its guests on `pve-lab`, live: `qm migrate <vmid> pve-lab --online --with-local-disks --targetstorage local-lvm`.
   Leave the other hosts as they are.
2. A k3s server that cannot move is drained first (`kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`),
   so its pods restart elsewhere one by one. Without that, Kubernetes waits five minutes before it moves them, and
   every service with its single replica on that node is down meanwhile (observed on 2026-11-25).
3. Volumes of the `local-path` class stay on their node: what uses them waits for the node to return.
4. Afterwards: `kubectl uncordon <node>`, move the guests back, check PostgreSQL (`patronictl list`) and the runners.

## Known issues

<!-- map:issues:start -->
| Known issue | Status | Summary |
|---|---|---|
| [Bursts of full-size frames are lost on the way into the Intel I219 hosts](/docs/issues/bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte) | open | pve-core and pve-management lose 3 to 5 % of back-to-back full-size frames they receive; TCP from faster hosts falls to 20-60 Mbit/s. Cause not fixed yet. |
<!-- map:issues:end -->

## Investigations

[New cluster inventory](/docs/investigations/new-proxmox-cluster-inventory),
[legacy inventory](/docs/investigations/legacy-inventory),
[bootstrap of pve-management](/docs/investigations/pve-management-bootstrap).
