---
title: Infrastructure inventory
description: 'Devices, cabling, networks, addresses and virtual machines of the homelab, generated from NetBox: change NetBox or services/netbox/inventory.yaml, not this page.'
published: true
tags:
- reference
- current
- netbox
- inventory
- hardware
- network
editor: markdown
date: '2026-11-21T00:00:00.000Z'
dateCreated: '2026-11-21T00:00:00.000Z'
---

# Infrastructure inventory

> **ID:** DOC-infrastructure-inventory · **Type:** reference · **Status:** current · **Updated:** 2026-11-21 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/reference/infrastructure-inventory.md)

This page is written by `make netbox-docs` from [NetBox](https://netbox.doku-lab.net) (LAN only), which is where
the inventory lives; NetBox also draws it (Topology Views for the network, Floorplan for the room). To change
something, change it where it is owned, then run the reconciliation and this target again:

- what a device is, its ports and addresses, what the old guests are: `services/netbox/inventory.yaml`;
- where a device sits, asset tags, comments: NetBox itself;
- the VMs of the platform: the OpenTofu roots under `terraform/stacks/`;
- state, size and hardware: read from the machines (`make netbox-discover`, `make netbox-discover-hardware`).

Serial numbers and hardware addresses are in NetBox only. "(to verify)" marks a record nobody has checked.

<!-- netbox:generated:start -->
## Devices

| Device | Role | Model | Address | Rack | Status | Description |
|---|---|---|---|---|---|---|
| access-point | Access point | TP-Link EAP220 | 192.168.0.2/24 |  | Active | Wi-Fi access point, managed on its own web interface |
| pfsense | Router | Lenovo ThinkCentre M75q Gen 2 | 192.168.0.1/24 |  | Active | AMD Ryzen 3, 8 GB RAM. pfSense, LAN gateway and DHCP; never changed or signed in to by automation |
| pve-core | Hypervisor | Lenovo ThinkStation P350 Tiny | 192.168.0.11/24 |  | Active | Intel Core i7-11700, 32 GB RAM, 1 TB NVMe |
| pve-infra | Hypervisor | Beelink Mini S | 192.168.0.12/24 |  | Active | Intel Celeron N5095A, 8 GB RAM, 256 GB SATA SSD |
| pve-lab | Hypervisor | ORIGIMAGIC Nebula Series | 192.168.0.16/24 |  | Active | AMD Ryzen 7 6800H, 28 GB usable RAM, 512 GB NVMe |
| pve-lab-legacy | Hypervisor | Custom build Tower, ASUS mainboard, Ryzen 9 9950X3D | 192.168.0.14/24 |  | Active (to verify) | Old environment (Proxmox node name pve-lab, future pve-compute). AMD Ryzen 9 9950X3D, 32 GB RAM |
| pve-management | Hypervisor | Lenovo ThinkCentre M90q | 192.168.0.10/24 |  | Active | Intel Core i5-10500T, 16 GB RAM, 256 GB NVMe; hosts the admin workstation (ADR-002) |
| switch | Switch | QNAP QSW-M3216R-8S8T | 192.168.0.116/24 | rack-01 | Active | Core switch; every Proxmox host of doku-lab is plugged into it. Its address is a DHCP lease until 192.168.0.3 is set on it |
| truenas | NAS | Custom build NAS, ASRock N100M mainboard | 192.168.0.13/24 |  | Active | TrueNAS: Forgejo, Nextcloud, Plex, qBittorrent; pools tank (2 x 8 TB mirror), fastpool (1 TB), apps-pool (180 GB). Not built from this repository |

## Cabling

| From | To | Cable | Known from |
|---|---|---|---|
| pve-core nic0 | switch 8 |  | announced by the switch (LLDP) |
| pve-infra nic0 | switch 7 |  | announced by the switch (LLDP) |
| pve-lab nic0 | switch 6 |  | announced by the switch (LLDP) |
| pve-management nic0 | switch 5 |  | announced by the switch (LLDP) |

## Hardware of the hosts

| Device | Part | Kind | Model | Details |
|---|---|---|---|---|
| pve-core | nvme0n1 | Disk | KINGSTON SNVS1000G | 1000 GB nvme |
| pve-core | Memory 1 | Memory | 9905700-122.A00G | 16 GB DDR4 3200 MT/s |
| pve-core | Memory 2 | Memory | 9905700-095.A00G | 16 GB DDR4 3200 MT/s |
| pve-core | CPU | Processor | 11th Gen Intel(R) Core(TM) i7-11700 @ 2.50GHz | 8 cores, 16 threads |
| pve-infra | sda | Disk | NGFF 2280 256GB SSD | 256 GB sata |
| pve-infra | Memory 1 | Memory | DDR4 NB 8G 2666 | 8 GB DDR4 2667 MT/s |
| pve-infra | CPU | Processor | Intel(R) Celeron(R) N5095A @ 2.00GHz | 4 cores, 4 threads |
| pve-lab | nvme0n1 | Disk | HighRel 512GB SSD | 512 GB nvme |
| pve-lab | Memory 1 | Memory |  | 16 GB DDR5 4800 MT/s |
| pve-lab | Memory 2 | Memory |  | 16 GB DDR5 4800 MT/s |
| pve-lab | CPU | Processor | AMD Ryzen 7 6800H with Radeon Graphics | 8 cores, 16 threads |
| pve-management | nvme0n1 | Disk | KBG6AZNV256G LA KIOXIA | 256 GB nvme |
| pve-management | Memory 1 | Memory | HMA82GS6DJR8N-VK | 16 GB DDR4 2667 MT/s |
| pve-management | CPU | Processor | Intel(R) Core(TM) i5-10500T CPU @ 2.30GHz | 6 cores, 12 threads |

## Networks

| Prefix | Role | Status | Description |
|---|---|---|---|
| 10.42.0.0/16 | Kubernetes | Active | k3s pod network (ansible/roles/k3s/defaults); exists only inside the cluster |
| 10.43.0.0/16 | Kubernetes | Active | k3s service network (ansible/roles/k3s/defaults); exists only inside the cluster |
| 100.64.0.0/10 | Overlay network | Container | Tailscale addresses (tailnet); ts-router-01 and ts-router-02 route the LAN to it |
| 192.168.0.0/24 |  | Active | LAN, gateway 192.168.0.1 (pfSense) |

| Address range | For | Description |
|---|---|---|
| 192.168.0.40 to 192.168.0.49 | k3s server | k3s nodes (VMIDs 310-349) |
| 192.168.0.50 to 192.168.0.59 | Storage | Storage VMs (VMIDs 350-359) |
| 192.168.0.60 to 192.168.0.69 | PostgreSQL | PostgreSQL: .60 virtual IP, .61-.69 members (VMIDs 360-369) |
| 192.168.0.70 to 192.168.0.79 | DNS | DNS VMs (VMIDs 370-379) |
| 192.168.0.100 to 192.168.0.200 |  | DHCP pool (pfSense), as stated in the k3s root; leases seen between .101 and .130 on 2026-11-20, the limits are not read from pfSense |

## Virtual machines and containers

### Cluster doku-lab

| Name | VMID | Host | Role | System | vCPU | Memory | Disk | Address | Status | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| mgmt-control-01 | 100 | pve-management | Admin workstation | Ubuntu 26.04 | 12 | 10 GB | 120 GB | 192.168.0.39/24 | Active | terraform/stacks/pve-management-control |
| deploy-runner-01 | 302 | pve-core | Deployment runner | Debian 13 | 6 | 8 GB | 24 GB | 192.168.0.32/24 | Active | terraform/stacks/deploy-runner |
| k3s-server-01 | 310 | pve-lab | k3s server | Debian 13 | 6 | 12 GB | 64 GB | 192.168.0.40/24 | Active | terraform/stacks/k3s |
| k3s-server-02 | 311 | pve-core | k3s server | Debian 13 | 4 | 8 GB | 64 GB | 192.168.0.41/24 | Active | terraform/stacks/k3s |
| k3s-server-03 | 312 | pve-lab | k3s server | Debian 13 | 4 | 6 GB | 64 GB | 192.168.0.42/24 | Active | terraform/stacks/k3s |
| storage-01 | 350 | pve-core | Storage | Debian 13 | 2 | 2 GB | 316 GB | 192.168.0.50/24 | Active | terraform/stacks/storage |
| pg-01 | 361 | pve-core | PostgreSQL | Debian 13 | 2 | 4 GB | 56 GB | 192.168.0.61/24 | Active | terraform/stacks/postgresql |
| pg-02 | 362 | pve-lab | PostgreSQL | Debian 13 | 2 | 4 GB | 56 GB | 192.168.0.62/24 | Active | terraform/stacks/postgresql |
| pg-03 | 363 | pve-infra | PostgreSQL | Debian 13 | 2 | 2 GB | 56 GB | 192.168.0.63/24 | Active | terraform/stacks/postgresql |
| dns-01 | 370 | pve-infra | DNS | Debian 13 | 1 | 1 GB | 16 GB | 192.168.0.70/24 | Active | terraform/stacks/dns |

### Cluster homelab

| Name | VMID | Host | Role | System | vCPU | Memory | Disk | Address | Status | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| print-server | 203 | pve-lab-legacy | Legacy service | Debian | 1 | 0.25 GB | 4 GB | 192.168.0.23/24 | Offline (to verify) | Print server (CUPS, print.home); stopped since the rack restart of 2026-11-19 |
| caddy | 204 | pve-lab-legacy | Legacy service | Debian | 2 | 1 GB | 8 GB | 192.168.0.24/24 | Active | Caddy: still serves git and cloud and the public tunnel (TASK-022) |
| vaultwarden | 206 | pve-lab-legacy | Legacy service | Debian | 1 | 0.75 GB | 8 GB | 192.168.0.26/24 | Active | Vaultwarden (vault.doku-lab.net, through the k3s ingress); not migrated yet |
| garage | 209 | pve-lab-legacy | Legacy service | Debian | 1 | 1 GB | 16 GB | 192.168.0.29/24 | Offline (to verify) | Garage object storage (ansible/playbooks/configure-garage.yml); stopped |
| tfstate | 300 | pve-lab-legacy | Legacy service | Debian | 1 | 2 GB | 16 GB | 192.168.0.30/24 | Offline (to verify) | OpenTofu state backups (tfstate.doku-lab.net); stopped |
| forgejo-runner-migration | 301 | pve-lab-legacy | Deployment runner | Debian | 4 | 6 GB | 38 GB | 192.168.0.31/24 | Active | Forgejo Actions runner of this repository (CT301); never holds Proxmox credentials (ADR-008) |
| ts-router-01 | 306 | pve-lab-legacy | Tailscale router | Debian | 1 | 0.5 GB | 8 GB | 192.168.0.36/24 | Active | Tailscale subnet router for the LAN (ansible/playbooks/configure-tailscale-routers.yml) |
| ts-router-02 | 307 | pve-lab-legacy | Tailscale router | Debian | 1 | 0.5 GB | 8 GB | 192.168.0.37/24 | Active | Tailscale subnet router for the LAN (ansible/playbooks/configure-tailscale-routers.yml) |

11 desktop and template machines of this cluster are in NetBox and not listed here.

### Cluster truenas

| Name | VMID | Host | Role | System | vCPU | Memory | Disk | Address | Status | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| pbs |  | truenas | Backup server | Proxmox Backup Server | 2 | 4 GB |  | 192.168.0.15/24 | Offline | Proxmox Backup Server, a VM on TrueNAS. Stopped: its backup disk failed in November 2026 |

## Addresses

| Address | On | Name | Kind | Description |
|---|---|---|---|---|
| 192.168.0.1/24 | pfsense lan | pfsense.doku-lab.net |  | pfsense |
| 192.168.0.2/24 | access-point eth0 |  |  | access-point |
| 192.168.0.3/24 |  | switch.doku-lab.net | Reserved | Meant for the switch (operator, 2026-11-21); not set on it yet, the switch answers at 192.168.0.116 |
| 192.168.0.9/24 | pve-core amt |  |  | pve-core |
| 192.168.0.10/24 | pve-management vmbr0 |  |  | pve-management |
| 192.168.0.11/24 | pve-core vmbr0 |  |  | pve-core |
| 192.168.0.12/24 | pve-infra vmbr0 |  |  | pve-infra |
| 192.168.0.13/24 | truenas bond0 |  |  | truenas |
| 192.168.0.14/24 | pve-lab-legacy vmbr0 |  |  | pve-lab-legacy |
| 192.168.0.15/24 | pbs net0 |  | Reserved | pbs |
| 192.168.0.16/24 | pve-lab vmbr0 |  |  | pve-lab |
| 192.168.0.20/24 | dns-01 net0 | adguard.doku-lab.net | Secondary | LAN DNS service address (ansible/vars/dns.yml) |
| 192.168.0.23/24 | print-server net0 |  |  | print-server |
| 192.168.0.24/24 | caddy net0 |  |  | caddy |
| 192.168.0.26/24 | vaultwarden net0 |  |  | vaultwarden |
| 192.168.0.29/24 | garage net0 |  |  | garage |
| 192.168.0.30/24 | tfstate net0 |  |  | tfstate |
| 192.168.0.31/24 | forgejo-runner-migration net0 |  |  | forgejo-runner-migration |
| 192.168.0.32/24 | deploy-runner-01 net0 |  |  | deploy-runner-01 |
| 192.168.0.36/24 | ts-router-01 net0 |  |  | ts-router-01 |
| 192.168.0.37/24 | ts-router-02 net0 |  |  | ts-router-02 |
| 192.168.0.39/24 | mgmt-control-01 net0 |  |  | mgmt-control-01 |
| 192.168.0.40/24 | k3s-server-01 net0 |  |  | k3s-server-01 |
| 192.168.0.41/24 | k3s-server-02 net0 |  |  | k3s-server-02 |
| 192.168.0.42/24 | k3s-server-03 net0 |  |  | k3s-server-03 |
| 192.168.0.50/24 | storage-01 net0 |  |  | storage-01 |
| 192.168.0.60/24 |  |  | VIP | PostgreSQL primary (Patroni virtual IP, terraform/stacks/postgresql) |
| 192.168.0.61/24 | pg-01 net0 |  |  | pg-01 |
| 192.168.0.62/24 | pg-02 net0 |  |  | pg-02 |
| 192.168.0.63/24 | pg-03 net0 |  |  | pg-03 |
| 192.168.0.70/24 | dns-01 net0 |  |  | dns-01 |
| 192.168.0.116/24 | switch vlan1 |  | DHCP | switch |

## Services

| Machine | Service | Protocol | Ports | Description |
|---|---|---|---|---|
| access-point | Web interface | TCP | 443 |  |
| dns-01 | AdGuard Home web interface | TCP | 80 |  |
| dns-01 | DNS | UDP | 53 |  |
| k3s-server-01 | Ingress (Traefik) | TCP | 80, 443 |  |
| k3s-server-01 | Kubernetes API | TCP | 6443 |  |
| k3s-server-02 | Ingress (Traefik) | TCP | 80, 443 |  |
| k3s-server-02 | Kubernetes API | TCP | 6443 |  |
| k3s-server-03 | Ingress (Traefik) | TCP | 80, 443 |  |
| k3s-server-03 | Kubernetes API | TCP | 6443 |  |
| pg-01 | PostgreSQL | TCP | 5432 | Clients use the virtual IP 192.168.0.60 |
| pg-02 | PostgreSQL | TCP | 5432 | Clients use the virtual IP 192.168.0.60 |
| pg-03 | PostgreSQL | TCP | 5432 | Clients use the virtual IP 192.168.0.60 |
| storage-01 | NFS | TCP | 2049 |  |
| switch | Web interface | TCP | 80, 443 |  |
| truenas | Forgejo | TCP | 30142, 30143 | git.doku-lab.net, through the legacy Caddy |
| truenas | Nextcloud | TCP | 30027 | cloud.doku-lab.net, through the legacy Caddy |
| truenas | TrueNAS web interface | TCP | 81, 444 |  |
<!-- netbox:generated:end -->
