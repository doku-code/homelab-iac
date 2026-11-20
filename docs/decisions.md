---
title: Decisions
description: 'Decisions: index of docs/decisions/ in the homelab-iac repository'
published: true
tags:
- index
editor: markdown
---

# Decisions

> Generated from the repository: [docs/decisions/](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/)

## Documents

| Document | Status | Summary |
|----------|--------|---------|
| [ADR-001: Rolling infrastructure rebuild](/docs/decisions/adr-001-rolling-infrastructure-rebuild) | accepted | Rebuild service by service using the running homelab to provision its replacement; no big-bang rebuild, no full hardware duplication. |
| [ADR-002: pve-management as a standalone host](/docs/decisions/adr-002-pve-management-standalone-host) | superseded | The fresh Proxmox host pve-management stays outside the compute cluster and runs only management VMs (IaC toolchain, runner, later Windmill/Phase). |
| [ADR-003: OpenTofu for new infrastructure](/docs/decisions/adr-003-opentofu-for-new-infrastructure) | accepted | New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan. |
| [ADR-004: Secrets — Phase at runtime, SOPS + age for bootstrap](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap) | accepted | Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill. |
| [ADR-005: Windmill over a versioned service catalog](/docs/decisions/adr-005-windmill-service-catalog) | accepted | Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo. |
| [ADR-006: Compose first, Kubernetes later](/docs/decisions/adr-006-compose-first-kubernetes-later) | superseded | Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction. |
| [ADR-007: Archive the legacy workflow, keep live roots](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots) | accepted | Old AGENTS.md, roadmap, tasks and docs moved verbatim to docs/archive/codex-2026; legacy Terraform/Ansible code that still manages live resources stays at its path. |
| [ADR-008: Workstation bootstrap, validation-only CI](/docs/decisions/adr-008-workstation-bootstrap-ct301-validation-only) | accepted | The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later. |
| [ADR-009: Management VM as a GNOME admin workstation](/docs/decisions/adr-009-management-vm-gnome-admin-workstation) | accepted | mgmt-control-01 is a GNOME admin workstation (Ubuntu 26.04, 8 vCPU host type, 10 GiB, 120 GiB) with RDP remote login, the IaC toolchain, Claude Code and Codex. |
| [ADR-010: New Proxmox cluster founded on pve-management](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management) | accepted | pve-management founds the new Proxmox cluster; the emptied pve-core joins first, every reclaimed host follows by the same repeatable process. Supersedes ADR-002. |
| [ADR-011: k3s first, Argo CD for GitOps, Headlamp for administration](/docs/decisions/adr-011-k3s-first-argocd-headlamp) | accepted | New applications run on k3s (OpenTofu VMs, Ansible bootstrap, embedded etcd); Argo CD reconciles them from Forgejo; Headlamp is the Kubernetes UI; Windmill automates workflows. Supersedes ADR-006. |
| [ADR-012: External NVMe-backed Kubernetes storage, TrueNAS for backups, Ceph later](/docs/decisions/adr-012-external-nvme-storage-truenas-backups) | accepted | PVCs come through CSI from NVMe-backed storage outside k3s on the physical hosts; TrueNAS only receives backups; Ceph (RBD, CephFS) is the future distributed layer. |
| [ADR-013: Central PostgreSQL with Patroni](/docs/decisions/adr-013-central-postgresql-patroni) | accepted | Applications get their own database, role and credentials on a shared PostgreSQL platform managed by Patroni (Zalando Postgres Operator pending validation), on external NVMe-backed PVCs. |
| [ADR-014: Dedicated Forgejo deployment runner](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner) | accepted | A runner VM created with OpenTofu and configured with Ansible runs approved OpenTofu, Ansible, k3s and Helm jobs with scoped credentials; CT301 stays validation-only. Amends ADR-008. |
| [ADR-015: PostgreSQL runs on three Patroni VMs outside k3s](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s) | accepted | Operator decision 2026-11-17: the shared PostgreSQL platform is three Patroni VMs outside k3s with etcd and a virtual IP, not an operator inside k3s. |
| [ADR-016: NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f) | accepted | NetBox on k3s holds the intended inventory and address plan; Git owns what OpenTofu defines, Proxmox is only observed, NetBox is never a bootstrap dependency. |
| [ADR-017: Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency](/docs/decisions/adr-017-authentik-is-the-single-sign-on-of-the-platform-declared-in) | accepted | Authentik on k3s signs people in to the web interfaces; applications and groups are blueprints in Git, people live in Authentik, and each service keeps a local administrator. |
