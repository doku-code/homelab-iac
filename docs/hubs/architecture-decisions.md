---
id: GUIDE-map-decisions
title: "Architecture decisions"
summary: "Every decision record, its status and what it replaced."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, decisions]
nav_order: 9
related: [DOC-project-overview]
related_decisions: []
source_paths: [scripts/docs-maps.py]
---

# Architecture decisions

A decision record states one choice, why it was made and what it costs. A record is a snapshot: a later record
replaces it, it is not rewritten. New one: `.venv/bin/harness new decision "<title>" --summary "<one line>"`.

<!-- map:decisions:start -->
| ID | Decision | Status | Date | Notes |
|---|---|---|---|---|
| ADR-001 | [Rolling infrastructure rebuild — the old infrastructure builds the new](../decisions/ADR-001-rolling-infrastructure-rebuild.md) | accepted | 2026-11-12 |  |
| ADR-002 | [pve-management is a standalone bootstrap, orchestration and recovery host](../decisions/ADR-002-pve-management-standalone-host.md) | superseded | 2026-11-12 | replaced by ADR-010 |
| ADR-003 | [OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually](../decisions/ADR-003-opentofu-for-new-infrastructure.md) | accepted | 2026-11-12 |  |
| ADR-004 | [Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets](../decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md) | accepted | 2026-11-12 |  |
| ADR-005 | [Windmill is the operations UI over a versioned service catalog](../decisions/ADR-005-windmill-service-catalog.md) | accepted | 2026-11-12 |  |
| ADR-006 | [Docker Compose first; k3s and Argo CD later, only where they add value](../decisions/ADR-006-compose-first-kubernetes-later.md) | superseded | 2026-11-12 | replaced by ADR-011 |
| ADR-007 | [Archive the legacy Codex workflow; keep live legacy IaC roots in place until migrated](../decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md) | accepted | 2026-11-12 |  |
| ADR-008 | [Bootstrap runs from the operator workstation; CT301 stays validation-only](../decisions/ADR-008-workstation-bootstrap-ct301-validation-only.md) | accepted | 2026-11-12 |  |
| ADR-009 | [The management VM is the operator's GNOME admin workstation](../decisions/ADR-009-management-vm-gnome-admin-workstation.md) | accepted | 2026-11-14 |  |
| ADR-010 | [The new Proxmox cluster is founded on pve-management and grows with reclaimed hosts](../decisions/ADR-010-new-proxmox-cluster-on-pve-management.md) | accepted | 2026-11-14 | replaces ADR-002 |
| ADR-011 | [k3s is the application platform from the start, reconciled by Argo CD and administered with Headlamp](../decisions/ADR-011-k3s-first-argocd-headlamp.md) | accepted | 2026-11-14 | replaces ADR-006 |
| ADR-012 | [Kubernetes persistent data lives on NVMe-backed storage outside k3s; TrueNAS is the backup destination; Ceph later](../decisions/ADR-012-external-nvme-storage-truenas-backups.md) | accepted | 2026-11-14 |  |
| ADR-013 | [A central PostgreSQL platform with Patroni replication serves the applications](../decisions/ADR-013-central-postgresql-patroni.md) | accepted | 2026-11-14 |  |
| ADR-014 | [A dedicated Forgejo runner VM executes approved infrastructure workflows](../decisions/ADR-014-dedicated-forgejo-deployment-runner.md) | accepted | 2026-11-14 |  |
| ADR-015 | [PostgreSQL runs on three Patroni VMs outside k3s](../decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md) | accepted | 2026-11-17 |  |
| ADR-016 | [NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery](../decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md) | accepted | 2026-11-18 |  |
| ADR-017 | [Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency](../decisions/ADR-017-authentik-is-the-single-sign-on-of-the-platform-declared-in.md) | accepted | 2026-11-18 |  |
| ADR-018 | [NetBox holds the physical inventory: Git says what a device is, machines report their hardware, people place it](../decisions/ADR-018-netbox-holds-the-physical-inventory-git-says-what-a-device-i.md) | accepted | 2026-11-21 |  |
<!-- map:decisions:end -->

Which decision governs which concern: [architecture map](architecture-map.md), "Responsibilities".
