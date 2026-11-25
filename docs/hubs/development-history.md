---
title: Development history
description: Milestones, the tasks under each and what is open now.
published: true
tags:
- guide
- current
- map
- roadmap
- history
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Development history

> **ID:** GUIDE-map-history · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/development-history.md)

Git is the history; milestones and tasks record why and with what evidence. Progress bars:
[dashboard](/docs/dashboard). The order of the milestones as a picture: [dependency map](/docs/hubs/dependency-map).

## Open tasks

<!-- map:tasks:start -->
| ID | Task | Status | Milestone | Updated |
|---|---|---|---|---|
| TASK-001 | [Reset repository to the agent harness and record the rebuild direction](/tasks/task-001-repository-reset-and-alignment) | in-progress | M000 | 2026-11-14 |
| TASK-002 | [Live read-only inventory of Proxmox hosts, guests and storage](/tasks/task-002-live-proxmox-inventory) | planned | M000 | 2026-11-12 |
| TASK-003 | [Service dependency, network/DNS and data/backup map](/tasks/task-003-service-dependency-and-data-map) | planned | M010 | 2026-11-14 |
| TASK-004 | [Representative PBS restore test](/tasks/task-004-pbs-representative-restore) | planned | M012 | 2026-11-14 |
| TASK-005 | [Migration order and bootstrap credential requirements](/tasks/task-005-migration-order-and-bootstrap-credentials) | planned | M010 | 2026-11-14 |
| TASK-006 | [Target repository layout, OpenTofu toolchain and management Make targets](/tasks/task-006-target-layout-and-service-contract) | in-progress | M001 | 2026-11-12 |
| TASK-011 | [SOPS + age bootstrap secrets](/tasks/task-011-sops-age-bootstrap-secrets) | planned | M012 | 2026-11-14 |
| TASK-012 | [Independent bootstrap and recovery runbook](/tasks/task-012-bootstrap-and-recovery-runbook) | planned | M012 | 2026-11-14 |
| TASK-019 | [Phase on k3s with the shared PostgreSQL and migration from Infisical](/tasks/task-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i) | in-progress | M008 | 2026-11-18 |
| TASK-022 | [Edge migration: certificates, Caddy sites on Traefik, AdGuard as code](/tasks/task-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a) | in-progress | M010 | 2026-11-23 |
| TASK-030 | [NetBox as the full inventory: real hardware, ports, cables, guests and diagram plugins](/tasks/task-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues) | in-progress | M013 | 2026-11-22 |
| TASK-035 | [Documentation maps: hub pages generated from the repository and a wiki with a curated sidebar](/tasks/task-035-documentation-maps-hub-pages-generated-from-the-repository-a) | in-progress | M010 | 2026-11-25 |
<!-- map:tasks:end -->

## Milestones

<!-- map:milestones:start -->
| ID | Milestone | Status | After | Tasks |
|---|---|---|---|---|
| M000 | [Infrastructure inventory and migration planning](/milestones/m000-inventory-and-migration-planning) | active |  | [TASK-001](/tasks/task-001-repository-reset-and-alignment) (in-progress), [TASK-002](/tasks/task-002-live-proxmox-inventory) (planned) |
| M001 | [Management workstation](/milestones/m001-bootstrap-pve-management) | completed |  | [TASK-006](/tasks/task-006-target-layout-and-service-contract) (in-progress), [TASK-007](/tasks/task-007-pve-management-access) (completed), [TASK-008](/tasks/task-008-proxmox-guest-module-and-management-vm) (completed), [TASK-009](/tasks/task-009-management-vm-ansible-baseline) (completed), [TASK-010](/tasks/task-010-state-management-and-backups) (completed) |
| M002 | [New Proxmox cluster (four nodes)](/milestones/m002-proxmox-compute-capacity) | completed | M001 | [TASK-013](/tasks/task-013-reinstall-pve-core-and-form-cluster) (completed) |
| M003 | [Dedicated Forgejo deployment runner](/milestones/m003-deployment-runner) | completed | M002 | [TASK-014](/tasks/task-014-bootstrap-deployment-runner-vm) (completed) |
| M004 | [k3s bootstrap](/milestones/m004-k3s-bootstrap) | completed | M002 | [TASK-015](/tasks/task-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab) (completed) |
| M005 | [Headlamp](/milestones/m005-headlamp) | completed | M004 | [TASK-016](/tasks/task-016-headlamp-on-k3s-with-lan-only-ingress-and-token-login) (completed) |
| M006 | [External NVMe-backed storage](/milestones/m006-external-nvme-storage) | completed | M004 | [TASK-017](/tasks/task-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla) (completed) |
| M007 | [PostgreSQL platform](/milestones/m007-postgresql-platform) | completed | M006 | [TASK-018](/tasks/task-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir) (completed) |
| M008 | [Phase](/milestones/m008-phase) | completed | M007 | [TASK-019](/tasks/task-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i) (in-progress) |
| M009 | [Argo CD and Windmill](/milestones/m009-argocd-windmill) | active | M005, M008 | [TASK-024](/tasks/task-024-argo-cd-on-k3s-and-netbox-as-its-first-application) (completed), [TASK-025](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox) (completed) |
| M010 | [Rolling application migration](/milestones/m010-rolling-application-migration) | planned | M009 | [TASK-003](/tasks/task-003-service-dependency-and-data-map) (planned), [TASK-005](/tasks/task-005-migration-order-and-bootstrap-credentials) (planned) |
| M011 | [Ceph and infrastructure expansion](/milestones/m011-ceph-and-expansion) | planned | M010 |  |
| M012 | [Backups and finalization](/milestones/m012-backups-and-finalization) | planned | M010 | [TASK-004](/tasks/task-004-pbs-representative-restore) (planned), [TASK-011](/tasks/task-011-sops-age-bootstrap-secrets) (planned), [TASK-012](/tasks/task-012-bootstrap-and-recovery-runbook) (planned) |
| M013 | [NetBox inventory and IPAM](/milestones/m013-netbox-inventory-and-ipam) | active | M004, M006, M007 | [TASK-023](/tasks/task-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i) (completed), [TASK-025](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox) (completed), [TASK-030](/tasks/task-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues) (in-progress) |
| M014 | [Single sign-on with Authentik](/milestones/m014-single-sign-on-with-authentik) | active | M004, M007, M009 | [TASK-026](/tasks/task-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb) (completed) |
<!-- map:milestones:end -->
