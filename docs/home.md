---
title: homelab-iac
description: 'Entry page of the documentation: what the platform is, the cluster at a glance and the maps that answer one question each.'
published: true
tags:
- guide
- current
- map
- home
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# homelab-iac

> **ID:** GUIDE-home · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/home.md)

Infrastructure as Code for a self-hosted homelab under a **rolling rebuild**: the running infrastructure provisions
its replacement, one service at a time. OpenTofu creates the guests on the Proxmox cluster `doku-lab`, Ansible
configures them, k3s runs the applications and Argo CD keeps them equal to Git; Forgejo holds the source and runs CI.

**Proxmox → k3s → storage outside k3s → PostgreSQL + Patroni → Phase → Argo CD + Windmill → applications.**

This repository is the source of the documentation: the wikis are generated from `docs/`, `milestones/` and
`tasks/`. Where things stand today and what comes next: [handoff](/docs/handoff). Why the platform looks like this:
[project overview](/docs/project-overview) and [platform architecture](/docs/architecture/platform).

## Maps

Each map answers one question. Their tables and diagrams are not typed by hand: `make docs-maps` writes them from
the files that own the facts (the Argo CD applications, the Makefile, the DNS answers, the inventory page), and a
check fails when one of them no longer says what the repository says.

<!-- map:maps:start -->
| Map | Answers |
|---|---|
| [Architecture map](/docs/hubs/architecture-map) | How the pieces fit: the layers from the hardware to the applications, and which tool owns which concern. |
| [Infrastructure map](/docs/hubs/infrastructure-map) | Hosts, guests and how they are wired: which machine runs what, with its size and address. |
| [Service catalog](/docs/hubs/service-catalog) | Every service of the platform: its site, where it runs, what signs people in and where its data lives. |
| [Network and names](/docs/hubs/network-map) | Which name answers where: the LAN's DNS answers, the shared addresses and the route behind each name. |
| [Deployment map](/docs/hubs/deployment-map) | What deploys what: the OpenTofu root of each guest, the playbook that configures it and the Argo CD application of each service. |
| [Dependency map](/docs/hubs/dependency-map) | What needs what to run, the order in which the platform starts, and the order in which it was built. |
| [Identity and secrets map](/docs/hubs/identity-and-secrets-map) | Who signs in where and through what, and which secret-store path feeds which deployment. |
| [CI/CD map](/docs/hubs/ci-cd-map) | The Forgejo workflows, what starts them, which runner executes them and the checks they run. |
| [Architecture decisions](/docs/hubs/architecture-decisions) | Every decision record, its status and what it replaced. |
| [Operations](/docs/hubs/operations) | Day-to-day procedures: where the commands are, how to take a host down, what is known to be broken. |
| [Development history](/docs/hubs/development-history) | Milestones, the tasks under each and what is open now. |
<!-- map:maps:end -->

## The cluster at a glance

<!-- map:infrastructure-diagram:start -->
```mermaid
flowchart TB
  access_point["access-point · 192.168.0.2<br/>Access point"]
  pfsense["pfsense · 192.168.0.1<br/>Router"]
  subgraph pve_compute["pve-compute · 192.168.0.14"]
    deploy_runner_01["deploy-runner-01<br/>Deployment runner"]
    ci_runner_01["ci-runner-01<br/>CI runner"]
    k3s_server_01["k3s-server-01<br/>k3s server"]
    storage_01["storage-01<br/>Storage"]
    pg_03["pg-03<br/>PostgreSQL"]
  end
  subgraph pve_core["pve-core · 192.168.0.11"]
    ts_router_01["ts-router-01<br/>Tailscale router"]
    k3s_server_02["k3s-server-02<br/>k3s server"]
    pg_01["pg-01<br/>PostgreSQL"]
    dns_01["dns-01<br/>DNS"]
  end
  subgraph pve_infra["pve-infra · 192.168.0.12"]
    media_01["media-01<br/>Media"]
  end
  subgraph pve_lab["pve-lab · 192.168.0.16"]
    k3s_server_03["k3s-server-03<br/>k3s server"]
    pg_02["pg-02<br/>PostgreSQL"]
  end
  subgraph pve_management["pve-management · 192.168.0.10"]
    mgmt_control_01["mgmt-control-01<br/>Admin workstation"]
    ts_router_02["ts-router-02<br/>Tailscale router"]
  end
  switch["switch · 192.168.0.3<br/>Switch"]
  subgraph truenas["truenas · 192.168.0.13"]
    pbs["pbs<br/>Backup server"]
  end
  switch --- access_point
  switch --- pfsense
  switch --- pve_compute
  switch --- pve_core
  switch --- pve_infra
  switch --- pve_lab
  switch --- pve_management
  switch --- truenas
```
<!-- map:infrastructure-diagram:end -->

Details, sizes and addresses: [infrastructure map](/docs/hubs/infrastructure-map); every device, cable and address:
[infrastructure inventory](/docs/reference/infrastructure-inventory), written from NetBox.

## Working on the repository

| Need | Where |
|---|---|
| Current work, commands, known issues | [handoff](/docs/handoff) |
| Rules for people and agents | [AGENTS.md](/agents) |
| Roadmap and progress | [development history](/docs/hubs/development-history), [dashboard](/docs/dashboard) |
| Every document by type | [knowledge map](/docs/knowledge-map) |
