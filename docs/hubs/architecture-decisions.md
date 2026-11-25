---
title: Architecture decisions
description: Every decision record, its status and what it replaced.
published: true
tags:
- guide
- current
- map
- decisions
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Architecture decisions

> **ID:** GUIDE-map-decisions · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/architecture-decisions.md)

A decision record states one choice, why it was made and what it costs. A record is a snapshot: a later record
replaces it, it is not rewritten. New one: `.venv/bin/harness new decision "<title>" --summary "<one line>"`.

<!-- map:decisions:start -->
| ID | Decision | Status | Date | Notes |
|---|---|---|---|---|
| ADR-001 | [Rolling infrastructure rebuild — the old infrastructure builds the new](/docs/decisions/adr-001-rolling-infrastructure-rebuild) | accepted | 2026-11-12 |  |
| ADR-002 | [pve-management is a standalone bootstrap, orchestration and recovery host](/docs/decisions/adr-002-pve-management-standalone-host) | superseded | 2026-11-12 | replaced by ADR-010 |
| ADR-003 | [OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually](/docs/decisions/adr-003-opentofu-for-new-infrastructure) | accepted | 2026-11-12 |  |
| ADR-004 | [Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap) | accepted | 2026-11-12 |  |
| ADR-005 | [Windmill is the operations UI over a versioned service catalog](/docs/decisions/adr-005-windmill-service-catalog) | accepted | 2026-11-12 |  |
| ADR-006 | [Docker Compose first; k3s and Argo CD later, only where they add value](/docs/decisions/adr-006-compose-first-kubernetes-later) | superseded | 2026-11-12 | replaced by ADR-011 |
| ADR-007 | [Archive the legacy Codex workflow; keep live legacy IaC roots in place until migrated](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots) | accepted | 2026-11-12 |  |
| ADR-008 | [Bootstrap runs from the operator workstation; CT301 stays validation-only](/docs/decisions/adr-008-workstation-bootstrap-ct301-validation-only) | accepted | 2026-11-12 |  |
| ADR-009 | [The management VM is the operator's GNOME admin workstation](/docs/decisions/adr-009-management-vm-gnome-admin-workstation) | accepted | 2026-11-14 |  |
| ADR-010 | [The new Proxmox cluster is founded on pve-management and grows with reclaimed hosts](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management) | accepted | 2026-11-14 | replaces ADR-002 |
| ADR-011 | [k3s is the application platform from the start, reconciled by Argo CD and administered with Headlamp](/docs/decisions/adr-011-k3s-first-argocd-headlamp) | accepted | 2026-11-14 | replaces ADR-006 |
| ADR-012 | [Kubernetes persistent data lives on NVMe-backed storage outside k3s; TrueNAS is the backup destination; Ceph later](/docs/decisions/adr-012-external-nvme-storage-truenas-backups) | accepted | 2026-11-14 |  |
| ADR-013 | [A central PostgreSQL platform with Patroni replication serves the applications](/docs/decisions/adr-013-central-postgresql-patroni) | accepted | 2026-11-14 |  |
| ADR-014 | [A dedicated Forgejo runner VM executes approved infrastructure workflows](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner) | accepted | 2026-11-14 |  |
| ADR-015 | [PostgreSQL runs on three Patroni VMs outside k3s](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s) | accepted | 2026-11-17 |  |
| ADR-016 | [NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f) | accepted | 2026-11-18 |  |
| ADR-017 | [Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency](/docs/decisions/adr-017-authentik-is-the-single-sign-on-of-the-platform-declared-in) | accepted | 2026-11-18 |  |
| ADR-018 | [NetBox holds the physical inventory: Git says what a device is, machines report their hardware, people place it](/docs/decisions/adr-018-netbox-holds-the-physical-inventory-git-says-what-a-device-i) | accepted | 2026-11-21 |  |
<!-- map:decisions:end -->

Which decision governs which concern: [architecture map](/docs/hubs/architecture-map), "Responsibilities".
