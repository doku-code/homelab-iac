---
id: GUIDE-map-network
title: "Network and names"
summary: "Which name answers where: the LAN's DNS answers, the shared addresses and the route behind each name."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, network, dns, ingress]
nav_order: 4
related: [DOC-infrastructure-inventory]
related_decisions: [ADR-016]
source_paths: [scripts/docs-maps.py]
---

# Network and names

One LAN, 192.168.0.0/24, behind pfSense (never changed by automation). `dns-01` answers the names below for the LAN;
almost all of them point at the cluster's shared address, where Traefik picks the route and presents the
certificate that cert-manager keeps valid.

```mermaid
flowchart LR
  client["A machine on the LAN"] -->|asks a name| dns["dns-01 · 192.168.0.20<br/>AdGuard Home"]
  client -->|HTTPS| vip["192.168.0.45<br/>shared address, kube-vip"]
  vip --> traefik["Traefik on k3s"]
  traefik --> svc["Services on k3s"]
  traefik --> outside["TrueNAS, Proxmox hosts,<br/>switch, pfSense"]
  internet["Internet"] -->|Cloudflare tunnel| traefik
```

## Names answered on the LAN

From [`ansible/vars/dns.yml`](../../ansible/vars/dns.yml) (`make dns-configure` writes it to AdGuard Home); the route
is the file that names the host for Traefik.

<!-- map:names:start -->
| Name | LAN answer | Answered by | Route |
|---|---|---|---|
| `adguard.doku-lab.net` | 192.168.0.20 | dns-01 (AdGuard Home) |  |
| `argocd.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/argocd/access.yaml`](../../services/argocd/access.yaml) |
| `auth.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/authentik/access.yaml`](../../services/authentik/access.yaml) |
| `cloud.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `dropper.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `git.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `grafana.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/observability/access.yaml`](../../services/observability/access.yaml) |
| `headlamp.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/headlamp/values.yaml`](../../services/headlamp/values.yaml) |
| `home.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/homepage/access.yaml`](../../services/homepage/access.yaml) |
| `homepage.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/homepage/access.yaml`](../../services/homepage/access.yaml) |
| `netbox.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/netbox/access.yaml`](../../services/netbox/access.yaml) |
| `pbs.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `pfsense.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `phase.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/phase/access.yaml`](../../services/phase/access.yaml) |
| `plex.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `pve-compute.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/proxmox-routes.yaml`](../../services/ingress/proxmox-routes.yaml) |
| `pve-core.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/proxmox-routes.yaml`](../../services/ingress/proxmox-routes.yaml) |
| `pve-infra.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/proxmox-routes.yaml`](../../services/ingress/proxmox-routes.yaml) |
| `pve-lab.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/proxmox-routes.yaml`](../../services/ingress/proxmox-routes.yaml) |
| `pve-management.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/proxmox-routes.yaml`](../../services/ingress/proxmox-routes.yaml) |
| `qbit.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `switch.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `truenas.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/ingress/legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml) |
| `vault.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/vaultwarden/vaultwarden.yaml`](../../services/vaultwarden/vaultwarden.yaml) |
| `wiki.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/wiki/access.yaml`](../../services/wiki/access.yaml) |
| `windmill.doku-lab.net` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/windmill/access.yaml`](../../services/windmill/access.yaml) |
<!-- map:names:end -->

Addresses, ranges and prefixes: [infrastructure inventory](../reference/infrastructure-inventory.md) ("Networks",
"Addresses"). Known network problem: see [operations](operations.md).
