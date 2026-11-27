---
id: GUIDE-map-history
title: "Development history"
summary: "Milestones, the tasks under each and what is open now."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, roadmap, history]
nav_order: 11
related: [DOC-project-overview, GUIDE-handoff]
related_decisions: []
source_paths: [scripts/docs-maps.py]
---

# Development history

Git is the history; milestones and tasks record why and with what evidence. Progress bars:
[dashboard](../dashboard.md). The order of the milestones as a picture: [dependency map](dependency-map.md).

## Open tasks

<!-- map:tasks:start -->
| ID | Task | Status | Milestone | Updated |
|---|---|---|---|---|
| TASK-001 | [Reset repository to the agent harness and record the rebuild direction](../../tasks/TASK-001-repository-reset-and-alignment.md) | in-progress | M000 | 2026-11-14 |
| TASK-002 | [Live read-only inventory of Proxmox hosts, guests and storage](../../tasks/TASK-002-live-proxmox-inventory.md) | planned | M000 | 2026-11-12 |
| TASK-003 | [Service dependency, network/DNS and data/backup map](../../tasks/TASK-003-service-dependency-and-data-map.md) | planned | M010 | 2026-11-14 |
| TASK-004 | [Representative PBS restore test](../../tasks/TASK-004-pbs-representative-restore.md) | planned | M012 | 2026-11-14 |
| TASK-005 | [Migration order and bootstrap credential requirements](../../tasks/TASK-005-migration-order-and-bootstrap-credentials.md) | planned | M010 | 2026-11-14 |
| TASK-006 | [Target repository layout, OpenTofu toolchain and management Make targets](../../tasks/TASK-006-target-layout-and-service-contract.md) | in-progress | M001 | 2026-11-12 |
| TASK-011 | [SOPS + age bootstrap secrets](../../tasks/TASK-011-sops-age-bootstrap-secrets.md) | planned | M012 | 2026-11-14 |
| TASK-012 | [Independent bootstrap and recovery runbook](../../tasks/TASK-012-bootstrap-and-recovery-runbook.md) | planned | M012 | 2026-11-14 |
| TASK-019 | [Phase on k3s with the shared PostgreSQL and migration from Infisical](../../tasks/TASK-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i.md) | in-progress | M008 | 2026-11-18 |
| TASK-022 | [Edge migration: certificates, Caddy sites on Traefik, AdGuard as code](../../tasks/TASK-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a.md) | in-progress | M010 | 2026-11-23 |
| TASK-030 | [NetBox as the full inventory: real hardware, ports, cables, guests and diagram plugins](../../tasks/TASK-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues.md) | in-progress | M013 | 2026-11-22 |
| TASK-035 | [Documentation maps: hub pages generated from the repository and a wiki with a curated sidebar](../../tasks/TASK-035-documentation-maps-hub-pages-generated-from-the-repository-a.md) | in-progress | M010 | 2026-11-25 |
| TASK-036 | [Media services on pve-infra: Jellyfin, Seerr, Radarr, Sonarr and Prowlarr, one container each](../../tasks/TASK-036-media-stack-on-pve-infra-jellyfin-seerr-radarr-sonarr-prowla.md) | in-progress | M010 | 2026-11-27 |
| TASK-037 | [TrueNAS under management: metrics in Grafana, apps as code, housekeeping](../../tasks/TASK-037-truenas-under-management-metrics-in-grafana-apps-as-code-hou.md) | in-progress | M010 | 2026-11-27 |
| TASK-039 | [Charcoal Titanium: one design system for the services' interfaces](../../tasks/TASK-039-charcoal-titanium-one-design-system-for-the-services-interfa.md) | in-progress | M010 | 2026-11-27 |
<!-- map:tasks:end -->

## Milestones

<!-- map:milestones:start -->
| ID | Milestone | Status | After | Tasks |
|---|---|---|---|---|
| M000 | [Infrastructure inventory and migration planning](../../milestones/M000-inventory-and-migration-planning.md) | active |  | [TASK-001](../../tasks/TASK-001-repository-reset-and-alignment.md) (in-progress), [TASK-002](../../tasks/TASK-002-live-proxmox-inventory.md) (planned) |
| M001 | [Management workstation](../../milestones/M001-bootstrap-pve-management.md) | completed |  | [TASK-006](../../tasks/TASK-006-target-layout-and-service-contract.md) (in-progress), [TASK-007](../../tasks/TASK-007-pve-management-access.md) (completed), [TASK-008](../../tasks/TASK-008-proxmox-guest-module-and-management-vm.md) (completed), [TASK-009](../../tasks/TASK-009-management-vm-ansible-baseline.md) (completed), [TASK-010](../../tasks/TASK-010-state-management-and-backups.md) (completed) |
| M002 | [New Proxmox cluster (four nodes)](../../milestones/M002-proxmox-compute-capacity.md) | completed | M001 | [TASK-013](../../tasks/TASK-013-reinstall-pve-core-and-form-cluster.md) (completed) |
| M003 | [Dedicated Forgejo deployment runner](../../milestones/M003-deployment-runner.md) | completed | M002 | [TASK-014](../../tasks/TASK-014-bootstrap-deployment-runner-vm.md) (completed) |
| M004 | [k3s bootstrap](../../milestones/M004-k3s-bootstrap.md) | completed | M002 | [TASK-015](../../tasks/TASK-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab.md) (completed) |
| M005 | [Headlamp](../../milestones/M005-headlamp.md) | completed | M004 | [TASK-016](../../tasks/TASK-016-headlamp-on-k3s-with-lan-only-ingress-and-token-login.md) (completed) |
| M006 | [External NVMe-backed storage](../../milestones/M006-external-nvme-storage.md) | completed | M004 | [TASK-017](../../tasks/TASK-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla.md) (completed) |
| M007 | [PostgreSQL platform](../../milestones/M007-postgresql-platform.md) | completed | M006 | [TASK-018](../../tasks/TASK-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir.md) (completed) |
| M008 | [Phase](../../milestones/M008-phase.md) | completed | M007 | [TASK-019](../../tasks/TASK-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i.md) (in-progress) |
| M009 | [Argo CD and Windmill](../../milestones/M009-argocd-windmill.md) | active | M005, M008 | [TASK-024](../../tasks/TASK-024-argo-cd-on-k3s-and-netbox-as-its-first-application.md) (completed), [TASK-025](../../tasks/TASK-025-windmill-on-k3s-reading-its-data-from-netbox.md) (completed) |
| M010 | [Rolling application migration](../../milestones/M010-rolling-application-migration.md) | planned | M009 | [TASK-003](../../tasks/TASK-003-service-dependency-and-data-map.md) (planned), [TASK-005](../../tasks/TASK-005-migration-order-and-bootstrap-credentials.md) (planned) |
| M011 | [Ceph and infrastructure expansion](../../milestones/M011-ceph-and-expansion.md) | planned | M010 |  |
| M012 | [Backups and finalization](../../milestones/M012-backups-and-finalization.md) | planned | M010 | [TASK-004](../../tasks/TASK-004-pbs-representative-restore.md) (planned), [TASK-011](../../tasks/TASK-011-sops-age-bootstrap-secrets.md) (planned), [TASK-012](../../tasks/TASK-012-bootstrap-and-recovery-runbook.md) (planned) |
| M013 | [NetBox inventory and IPAM](../../milestones/M013-netbox-inventory-and-ipam.md) | active | M004, M006, M007 | [TASK-023](../../tasks/TASK-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i.md) (completed), [TASK-025](../../tasks/TASK-025-windmill-on-k3s-reading-its-data-from-netbox.md) (completed), [TASK-030](../../tasks/TASK-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues.md) (in-progress) |
| M014 | [Single sign-on with Authentik](../../milestones/M014-single-sign-on-with-authentik.md) | active | M004, M007, M009 | [TASK-026](../../tasks/TASK-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb.md) (completed) |
<!-- map:milestones:end -->
