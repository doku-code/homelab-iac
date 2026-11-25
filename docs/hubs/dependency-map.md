---
title: Dependency map
description: What needs what to run, the order in which the platform starts, and the order in which it was built.
published: true
tags:
- guide
- current
- map
- dependencies
- bootstrap
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Dependency map

> **ID:** GUIDE-map-dependencies · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/dependency-map.md)

## At run time

An arrow reads "needs". Nothing below k3s needs k3s: the data, the names and the workstation keep working when the
cluster is down.

```mermaid
flowchart BT
  proxmox["Proxmox hosts"]
  dns["dns-01"] --> proxmox
  storage["storage-01, NFS"] --> proxmox
  pg["PostgreSQL, Patroni"] --> proxmox
  k3s["k3s servers"] --> proxmox
  k3s --> dns
  ingress["Traefik, cert-manager"] --> k3s
  argo["Argo CD"] --> k3s
  argo --> forgejo["Forgejo on TrueNAS"]
  authentik["Authentik"] --> pg
  authentik --> ingress
  apps["NetBox, Phase, Wiki.js,<br/>Windmill, Vaultwarden"] --> pg
  apps --> storage
  apps --> ingress
  apps -. sign-in .-> authentik
  monitoring["VictoriaMetrics, Loki, Grafana"] --> k3s
  monitoring -. sign-in .-> authentik
  forgejo --> ingress
```

- Every service keeps a local administrator: Authentik being down locks nobody out of the tools that repair it
  ([ADR-017](/docs/decisions/adr-017-authentik-is-the-single-sign-on-of-the-platform-declared-in)).
- No OpenTofu root needs NetBox to plan or apply ([ADR-016](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f)).
- Forgejo is reached through the ingress of the cluster it feeds: Argo CD keeps running what it already applied
  when Forgejo is away, and the workstation holds a full clone.

## Start order after a full stop

1. pfSense, the switch, the Proxmox hosts.
2. `dns-01`, then `storage-01` and the three PostgreSQL members.
3. The k3s servers; the shared address moves to whichever answers first.
4. Argo CD and the services follow by themselves.

Taking one host down for maintenance: see [operations](/docs/hubs/operations).

## Build order

The milestones and what each one waits for (green: completed, blue: active).

<!-- map:milestone-graph:start -->
```mermaid
flowchart LR
  M000["M000<br/>Infrastructure inventory and migration planning"]
  M001["M001<br/>Management workstation"]
  M002["M002<br/>New Proxmox cluster (four nodes)"]
  M003["M003<br/>Dedicated Forgejo deployment runner"]
  M004["M004<br/>k3s bootstrap"]
  M005["M005<br/>Headlamp"]
  M006["M006<br/>External NVMe-backed storage"]
  M007["M007<br/>PostgreSQL platform"]
  M008["M008<br/>Phase"]
  M009["M009<br/>Argo CD and Windmill"]
  M010["M010<br/>Rolling application migration"]
  M011["M011<br/>Ceph and infrastructure expansion"]
  M012["M012<br/>Backups and finalization"]
  M013["M013<br/>NetBox inventory and IPAM"]
  M014["M014<br/>Single sign-on with Authentik"]
  M001 --> M002
  M002 --> M003
  M002 --> M004
  M004 --> M005
  M004 --> M006
  M006 --> M007
  M007 --> M008
  M005 --> M009
  M008 --> M009
  M009 --> M010
  M010 --> M011
  M010 --> M012
  M004 --> M013
  M006 --> M013
  M007 --> M013
  M004 --> M014
  M007 --> M014
  M009 --> M014
  classDef completed fill:#1f5f3a,stroke:#2ea043,color:#fff
  class M001,M002,M003,M004,M005,M006,M007,M008 completed
  classDef active fill:#1f4b7a,stroke:#388bfd,color:#fff
  class M000,M009,M013,M014 active
```
<!-- map:milestone-graph:end -->
