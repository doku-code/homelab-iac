---
id: GUIDE-home
title: "homelab-iac"
summary: "Entry page of the documentation: what the platform is, the cluster at a glance and the maps that answer one question each."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, home]
nav_order: 0
related: [DOC-project-overview, ARCH-platform, GUIDE-handoff]
related_decisions: []
source_paths: [scripts/docs-maps.py]
---

# homelab-iac

Infrastructure as Code for a self-hosted homelab under a **rolling rebuild**: the running infrastructure provisions
its replacement, one service at a time. OpenTofu creates the guests on the Proxmox cluster `doku-lab`, Ansible
configures them, k3s runs the applications and Argo CD keeps them equal to Git; Forgejo holds the source and runs CI.

**Proxmox → k3s → storage outside k3s → PostgreSQL + Patroni → Phase → Argo CD + Windmill → applications.**

This repository is the source of the documentation: the wikis are generated from `docs/`, `milestones/` and
`tasks/`. Where things stand today and what comes next: [handoff](handoff.md). Why the platform looks like this:
[project overview](project-overview.md) and [platform architecture](architecture/platform.md).

## Maps

Each map answers one question. Their tables and diagrams are not typed by hand: `make docs-maps` writes them from
the files that own the facts (the Argo CD applications, the Makefile, the DNS answers, the inventory page), and a
check fails when one of them no longer says what the repository says.

<!-- map:maps:start -->
| Map | Answers |
|---|---|
| [Architecture map](hubs/architecture-map.md) | How the pieces fit: the layers from the hardware to the applications, and which tool owns which concern. |
| [Infrastructure map](hubs/infrastructure-map.md) | Hosts, guests and how they are wired: which machine runs what, with its size and address. |
| [Service catalog](hubs/service-catalog.md) | Every service of the platform: its site, where it runs, what signs people in and where its data lives. |
| [Network and names](hubs/network-map.md) | Which name answers where: the LAN's DNS answers, the shared addresses and the route behind each name. |
| [Deployment map](hubs/deployment-map.md) | What deploys what: the OpenTofu root of each guest, the playbook that configures it and the Argo CD application of each service. |
| [Dependency map](hubs/dependency-map.md) | What needs what to run, the order in which the platform starts, and the order in which it was built. |
| [Identity and secrets map](hubs/identity-and-secrets-map.md) | Who signs in where and through what, and which secret-store path feeds which deployment. |
| [CI/CD map](hubs/ci-cd-map.md) | The Forgejo workflows, what starts them, which runner executes them and the checks they run. |
| [Architecture decisions](hubs/architecture-decisions.md) | Every decision record, its status and what it replaced. |
| [Operations](hubs/operations.md) | Day-to-day procedures: where the commands are, how to take a host down, what is known to be broken. |
| [Development history](hubs/development-history.md) | Milestones, the tasks under each and what is open now. |
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
    pve_infra_empty["no guest of the platform"]
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

Details, sizes and addresses: [infrastructure map](hubs/infrastructure-map.md); every device, cable and address:
[infrastructure inventory](reference/infrastructure-inventory.md), written from NetBox.

## Working on the repository

| Need | Where |
|---|---|
| Current work, commands, known issues | [handoff](handoff.md) |
| Rules for people and agents | [AGENTS.md](../AGENTS.md) |
| Roadmap and progress | [development history](hubs/development-history.md), [dashboard](dashboard.md) |
| Every document by type | [knowledge map](knowledge-map.md) |
