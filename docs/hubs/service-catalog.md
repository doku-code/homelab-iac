---
id: GUIDE-map-services
title: "Service catalog"
summary: "Every service of the platform: its site, where it runs, what signs people in and where its data lives."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, services, k3s]
nav_order: 3
related: [ARCH-platform]
related_decisions: [ADR-011, ADR-017]
source_paths: [scripts/docs-maps.py]
---

# Service catalog

## On k3s, under Argo CD

One row per Argo CD application ([`services/argocd/apps`](../../services/argocd/apps)). One replica per service for
now. Argo CD itself is installed by `make argocd-deploy` from [`services/argocd`](../../services/argocd) and answers
on <https://argocd.doku-lab.net>.

<!-- map:services:start -->
| Service | Site | Namespace | Chart | Sign-in | Database |
|---|---|---|---|---|---|
| [authentik](../../services/authentik) | <https://auth.doku-lab.net> | `authentik` | authentik 2026.8.5 | its own | shared PostgreSQL |
| [headlamp](../../services/headlamp) | <https://headlamp.doku-lab.net> | `headlamp` | headlamp 0.46.0 | Authentik (OpenID Connect) |  |
| [homepage](../../services/homepage) | <https://homepage.doku-lab.net>, <https://home.doku-lab.net> | `homepage` | manifests of this repository | Authentik, in front of the service |  |
| [ingress](../../services/ingress) |  | `cert-manager` | cert-manager v1.21.3 |  |  |
| [monitoring](../../services/observability) | <https://grafana.doku-lab.net> | `monitoring` | victoria-metrics-single 0.52.0, victoria-metrics-alert 0.54.0, kube-state-metrics 9.1.0, loki 7.6.0, alloy 1.16.0, grafana 14.5.0 | Authentik (OpenID Connect) | shared PostgreSQL |
| [netbox](../../services/netbox) | <https://netbox.doku-lab.net> | `netbox` | netbox 8.3.107 | Authentik (OpenID Connect) | shared PostgreSQL |
| [phase](../../services/phase) | <https://phase.doku-lab.net> | `phase` | manifests of this repository | its own | shared PostgreSQL |
| [storage](../../services/storage) |  | `kube-system` | csi-driver-nfs 4.13.6 |  |  |
| [vaultwarden](../../services/vaultwarden) | <https://vault.doku-lab.net> | `vaultwarden` | manifests of this repository | its own | shared PostgreSQL |
| [wiki](../../services/wiki) | <https://wiki.doku-lab.net> | `wiki` | wiki 3.5.0 | Authentik (OpenID Connect) | shared PostgreSQL |
| [windmill](../../services/windmill) | <https://windmill.doku-lab.net> | `windmill` | windmill 4.0.324 | Authentik (OpenID Connect) | shared PostgreSQL |
<!-- map:services:end -->

## Outside k3s

| Service | Where | Why not on k3s |
|---|---|---|
| PostgreSQL 18 with Patroni | `pg-01`, `pg-02`, `pg-03`; clients use 192.168.0.60 | The applications' data must not depend on the cluster that runs them ([ADR-015](../decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md)) |
| NFS volumes | `storage-01` | Same reason ([ADR-012](../decisions/ADR-012-external-nvme-storage-truenas-backups.md)) |
| DNS for the LAN, AdGuard Home | `dns-01`, 192.168.0.20 | The cluster needs names to start |
| Forgejo runners | `ci-runner-01` (validation, no credentials), `deploy-runner-01` (gated deployments) | Separated by trust ([ADR-014](../decisions/ADR-014-dedicated-forgejo-deployment-runner.md)) |
| Tailscale subnet routers | `ts-router-01`, `ts-router-02` | Remote access must outlive the cluster |
| Forgejo, Nextcloud, Plex, qBittorrent | TrueNAS applications | Not part of the migration; reached through Traefik ([`legacy-routes.yaml`](../../services/ingress/legacy-routes.yaml)) |

Which name leads where: [network and names](network-map.md). How a service is deployed:
[deployment map](deployment-map.md).
