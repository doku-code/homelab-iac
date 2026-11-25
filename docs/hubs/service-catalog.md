---
title: Service catalog
description: 'Every service of the platform: its site, where it runs, what signs people in and where its data lives.'
published: true
tags:
- guide
- current
- map
- services
- k3s
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Service catalog

> **ID:** GUIDE-map-services · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/service-catalog.md)

## On k3s, under Argo CD

One row per Argo CD application ([`services/argocd/apps`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/argocd/apps/)). One replica per service for
now. Argo CD itself is installed by `make argocd-deploy` from [`services/argocd`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/argocd/) and answers
on <https://argocd.doku-lab.net>.

<!-- map:services:start -->
| Service | Site | Namespace | Chart | Sign-in | Database |
|---|---|---|---|---|---|
| [authentik](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/) | <https://auth.doku-lab.net> | `authentik` | authentik 2026.8.5 | its own | shared PostgreSQL |
| [headlamp](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/headlamp/) | <https://headlamp.doku-lab.net> | `headlamp` | headlamp 0.46.0 | Authentik (OpenID Connect) |  |
| [homepage](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/homepage/) | <https://homepage.doku-lab.net>, <https://home.doku-lab.net> | `homepage` | manifests of this repository | Authentik, in front of the service |  |
| [ingress](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/ingress/) |  | `cert-manager` | cert-manager v1.21.3 |  |  |
| [monitoring](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/observability/) | <https://grafana.doku-lab.net> | `monitoring` | victoria-metrics-single 0.52.0, victoria-metrics-alert 0.54.0, kube-state-metrics 9.1.0, loki 7.6.0, alloy 1.16.0, grafana 14.5.0 | Authentik (OpenID Connect) | shared PostgreSQL |
| [netbox](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/netbox/) | <https://netbox.doku-lab.net> | `netbox` | netbox 8.3.107 | Authentik (OpenID Connect) | shared PostgreSQL |
| [phase](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/phase/) | <https://phase.doku-lab.net> | `phase` | manifests of this repository | its own | shared PostgreSQL |
| [storage](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/storage/) |  | `kube-system` | csi-driver-nfs 4.13.6 |  |  |
| [vaultwarden](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/vaultwarden/) | <https://vault.doku-lab.net> | `vaultwarden` | manifests of this repository | its own | shared PostgreSQL |
| [wiki](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/wiki/) | <https://wiki.doku-lab.net> | `wiki` | wiki 3.5.0 | Authentik (OpenID Connect) | shared PostgreSQL |
| [windmill](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/windmill/) | <https://windmill.doku-lab.net> | `windmill` | windmill 4.0.324 | Authentik (OpenID Connect) | shared PostgreSQL |
<!-- map:services:end -->

## Outside k3s

| Service | Where | Why not on k3s |
|---|---|---|
| PostgreSQL 17 with Patroni | `pg-01`, `pg-02`, `pg-03`; clients use 192.168.0.60 | The applications' data must not depend on the cluster that runs them ([ADR-015](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s)) |
| NFS volumes | `storage-01` | Same reason ([ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups)) |
| DNS for the LAN, AdGuard Home | `dns-01`, 192.168.0.20 | The cluster needs names to start |
| Forgejo runners | `ci-runner-01` (validation, no credentials), `deploy-runner-01` (gated deployments) | Separated by trust ([ADR-014](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner)) |
| Tailscale subnet routers | `ts-router-01`, `ts-router-02` | Remote access must outlive the cluster |
| Forgejo, Nextcloud, Plex, qBittorrent | TrueNAS applications | Not part of the migration; reached through Traefik ([`legacy-routes.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/ingress/legacy-routes.yaml)) |

Which name leads where: [network and names](/docs/hubs/network-map). How a service is deployed:
[deployment map](/docs/hubs/deployment-map).
