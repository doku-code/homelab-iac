---
title: Tasks
description: 'Tasks: index of tasks/ in the homelab-iac repository'
published: true
tags:
- index
editor: markdown
---

# Tasks

> Generated from the repository: [tasks/](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/)

## Documents

| Document | Status | Summary |
|----------|--------|---------|
| [TASK-001 — Reset repository to the agent harness and record the rebuild direction](/tasks/task-001-repository-reset-and-alignment) | in-progress | Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap. |
| [TASK-002 — Live read-only inventory of Proxmox hosts, guests and storage](/tasks/task-002-live-proxmox-inventory) | planned | Verify hosts, cluster membership, VMs/LXCs, storage and capacity on every node; correct the legacy inventory. |
| [TASK-003 — Service dependency, network/DNS and data/backup map](/tasks/task-003-service-dependency-and-data-map) | planned | Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage. |
| [TASK-004 — Representative PBS restore test](/tasks/task-004-pbs-representative-restore) | planned | Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data. |
| [TASK-005 — Migration order and bootstrap credential requirements](/tasks/task-005-migration-order-and-bootstrap-credentials) | planned | Decide the service migration order and list every bootstrap credential and recovery prerequisite. |
| [TASK-006 — Target repository layout, OpenTofu toolchain and management Make targets](/tasks/task-006-target-layout-and-service-contract) | in-progress | Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check). |
| [TASK-007 — Scoped Proxmox API token and SSH access for pve-management](/tasks/task-007-pve-management-access) | completed | Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible. |
| [TASK-008 — Reusable OpenTofu guest module and management VM root](/tasks/task-008-proxmox-guest-module-and-management-vm) | completed | Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM. |
| [TASK-009 — Ansible baseline for the management VM (toolchain and runner)](/tasks/task-009-management-vm-ansible-baseline) | completed | Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008). |
| [TASK-010 — OpenTofu state management and backups](/tasks/task-010-state-management-and-backups) | completed | Keep new-root state local on the single operator workstation, move it from the Mac to mgmt-control-01, and never let an empty state recreate existing guests. |
| [TASK-011 — SOPS + age bootstrap secrets](/tasks/task-011-sops-age-bootstrap-secrets) | planned | Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows. |
| [TASK-012 — Independent bootstrap and recovery runbook](/tasks/task-012-bootstrap-and-recovery-runbook) | planned | Write and exercise the runbook that rebuilds the management VM from a clean workstation. |
| [TASK-013 — Reinstall pve-core and form the new Proxmox cluster](/tasks/task-013-reinstall-pve-core-and-form-cluster) | completed | Confirm the emptied pve-core holds nothing to keep, inventory its NVMe, reinstall Proxmox VE, create the cluster on pve-management and join pve-core with an explicit two-node quorum plan. |
| [TASK-014 — Bootstrap deployment runner VM on pve-core](/tasks/task-014-bootstrap-deployment-runner-vm) | completed | Runner VM deploy-runner-01 (VMID 302, .32) on pve-core via headless-vm, deploy_runner role, main-only wrapper, approval-gated dispatch workflow and a disposable proof root (ADR-014). |
| [TASK-015 — k3s cluster on doku-lab: first server on pve-lab](/tasks/task-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab) | completed | terraform/stacks/k3s VMs (for_each, rebuildable), k3s role with embedded etcd, token in Infisical /k3s, host keys pinned out-of-band, workstation kubeconfig (ADR-011). |
| [TASK-016 — Headlamp on k3s with LAN-only ingress and token login](/tasks/task-016-headlamp-on-k3s-with-lan-only-ingress-and-token-login) | completed | Official chart 0.46.0, no cluster rights for the app, admin ServiceAccount token in Infisical dev:/headlamp, HTTPS ingress limited to 192.168.0.0/24. |
| [TASK-017 — Shared NFS storage VM on pve-core and nvme-shared StorageClass](/tasks/task-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla) | completed | storage-01 (VM 350, .50, 300 GiB data disk) exports NFSv4 to the k3s nodes only; csi-driver-nfs 4.13.6 with a Retain class for user data; app data stays on local-path. |
| [TASK-018 — PostgreSQL platform: three Patroni VMs outside k3s with a virtual IP](/tasks/task-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir) | completed | Three Debian 13 VMs (pg-01..03 on pve-core, pve-lab, pve-infra) run PostgreSQL 17 under Patroni with etcd and a virtual IP; per-application databases and roles. |
| [TASK-019 — Phase on k3s with the shared PostgreSQL and migration from Infisical](/tasks/task-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i) | in-progress | Phase Console v2.79.0 runs on k3s with its database on the shared PostgreSQL; scripts/secrets.py selects the store, migrates and verifies; cutover waits for the operator's Phase account. |
| [TASK-020 — Lean observability: Prometheus, Loki, Grafana and Alloy](/tasks/task-020-lean-observability-prometheus-loki-grafana-and-alloy) | completed | Prometheus, Loki and Grafana on k3s; Alloy collects a small allow-list of metrics and logs from the cluster and from every VM; Grafana state on the shared PostgreSQL. |
| [TASK-021 — k3s servers on pve-core and pve-lab: three etcd members](/tasks/task-021-k3s-servers-on-pve-core-and-pve-lab-three-etcd-members) | completed | k3s-server-02 on pve-core and k3s-server-03 on pve-lab join the embedded etcd; Traefik runs on every node so ingress survives a reschedule. |
| [TASK-022 — Edge migration: certificates, Caddy sites on Traefik, AdGuard as code](/tasks/task-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a) | in-progress | Let's Encrypt wildcard on Traefik, the active Caddy sites as Traefik routes, then AdGuard rebuilt from code and the names moved from Caddy to the cluster. |
| [TASK-023 — NetBox on k3s, initial inventory, reconciliation and Ansible inventory](/tasks/task-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i) | completed | Deploy NetBox with the official chart on the shared PostgreSQL, populate it from the OpenTofu outputs and read-only Proxmox discovery, and let Ansible read its inventory from it. |
| [TASK-024 — Argo CD on k3s and every service of the cluster under it](/tasks/task-024-argo-cd-on-k3s-and-netbox-as-its-first-application) | completed | Install Argo CD, restrict it to this repository and named namespaces, and move every service of the cluster under it without a restart. |
| [TASK-025 — Windmill on k3s reading its data from NetBox](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox) | completed | Deploy Windmill under Argo CD on the shared PostgreSQL, bootstrap it without default credentials, and publish scripts from Git that read roles, ranges and free addresses from NetBox. |
| [TASK-026 — Authentik on k3s and single sign-on for Argo CD, Grafana, NetBox and Windmill](/tasks/task-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb) | completed | Authentik 2026.8.5 under Argo CD on the shared PostgreSQL; applications and groups as blueprints; OIDC sign-in wired for Argo CD, Grafana, NetBox and Windmill with local administrators kept. |
| [TASK-027 — Homepage on k3s behind Authentik, rearranged for the doku-lab cluster, with a new widget data API](/tasks/task-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab) | completed | The dashboard moved from legacy CT201 to k3s under Argo CD, behind Authentik forward authentication, with cards for the new platform and a widget API fed by Proxmox, Prometheus and HTTP checks. |
| [TASK-028 — Workstation VM renders on the host's graphics adapter](/tasks/task-028-workstation-vm-renders-on-the-host-s-graphics-adapter) | completed | VM 100 gets the Intel UHD 630 of pve-management through a resource mapping, all twelve host threads and Proxmox protection; cold start with automatic rollback. |
| [TASK-029 — Wiki.js 3 on k3s showing this repository's documentation](/tasks/task-029-wiki-js-3-on-k3s-showing-this-repository-s-documentation) | completed | Wiki.js 3.5 on k3s under Argo CD with the shared PostgreSQL and Authentik sign-in; its pages are generated from this repository and pulled by the wiki's Git storage. |
