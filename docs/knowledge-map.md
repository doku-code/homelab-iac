---
title: Knowledge map
description: ''
published: true
tags:
- index
- generated
editor: markdown
---

# Knowledge map

> **ID:** INDEX-knowledge-map · **Type:** index · **Status:** generated · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/knowledge-map.md)

Generated navigation index. Do not edit; regenerate with `harness docs index`.
Documents are the source of truth; this map only lists them.

How to use: find the row that matches your task (by type, tag, component or ID), open only that document, then follow its `related*` links. Use `harness docs search <terms>` for anything not visible here.

## Milestones

| ID | Status | Priority | Title | Tasks | Summary |
|----|--------|----------|-------|-------|---------|
| M000 | active | critical | [Infrastructure inventory and migration planning](/milestones/m000-inventory-and-migration-planning) | in-progress: 1, planned: 1 | Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime. |
| M009 | active | medium | [Argo CD and Windmill](/milestones/m009-argocd-windmill) | completed: 2 | Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner. |
| M013 | active | medium | [NetBox inventory and IPAM](/milestones/m013-netbox-inventory-and-ipam) | completed: 1, in-progress: 1 | NetBox runs on k3s as the inventory and IPAM source of truth, is populated from OpenTofu outputs and read-only Proxmox discovery, and Ansible can read its inventory from it. |
| M014 | active | medium | [Single sign-on with Authentik](/milestones/m014-single-sign-on-with-authentik) | completed: 1 | Authentik runs on k3s and signs the operator in to the web interfaces of the platform; each new service is added to it in the same change, and every service keeps a local administrator. |
| M010 | planned | high | [Rolling application migration](/milestones/m010-rolling-application-migration) | completed: 7, in-progress: 4, planned: 2 | Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster. |
| M011 | planned | medium | [Ceph and infrastructure expansion](/milestones/m011-ceph-and-expansion) | none | With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts. |
| M012 | planned | medium | [Backups and finalization](/milestones/m012-backups-and-finalization) | planned: 3 | Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired. |
| M001 | completed | critical | [Management workstation](/milestones/m001-bootstrap-pve-management) | completed: 5, in-progress: 1 | Existing infrastructure provisions and configures the management workstation VM on pve-management from IaC, and operations move to it. |
| M002 | completed | critical | [New Proxmox cluster (four nodes)](/milestones/m002-proxmox-compute-capacity) | completed: 1 | The new cluster doku-lab runs on pve-management, pve-core, pve-infra and the new pve-lab (.16), quorate, with its hardware and capacity inventoried. |
| M003 | completed | high | [Dedicated Forgejo deployment runner](/milestones/m003-deployment-runner) | completed: 1 | A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials. |
| M004 | completed | high | [k3s bootstrap](/milestones/m004-k3s-bootstrap) | completed: 2 | The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl. |
| M005 | completed | high | [Headlamp](/milestones/m005-headlamp) | completed: 1 | Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs. |
| M006 | completed | high | [External NVMe-backed storage](/milestones/m006-external-nvme-storage) | completed: 1 | Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented. |
| M007 | completed | high | [PostgreSQL platform](/milestones/m007-postgresql-platform) | completed: 1 | PostgreSQL 17 runs on three Patroni VMs outside k3s (one per Proxmox host) with automatic failover and a virtual IP; per-application databases and roles. |
| M008 | completed | high | [Phase](/milestones/m008-phase) | in-progress: 1 | Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it. |

## Tasks

| ID | Status | Priority | Milestone | Title | Summary |
|----|--------|----------|-----------|-------|---------|
| TASK-001 | in-progress | critical | M000 | [Reset repository to the agent harness and record the rebuild direction](/tasks/task-001-repository-reset-and-alignment) | Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap. |
| TASK-006 | in-progress | critical | M001 | [Target repository layout, OpenTofu toolchain and management Make targets](/tasks/task-006-target-layout-and-service-contract) | Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check). |
| TASK-019 | in-progress | high | M008 | [Phase on k3s with the shared PostgreSQL and migration from Infisical](/tasks/task-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i) | Phase Console v2.79.0 runs on k3s with its database on the shared PostgreSQL; scripts/secrets.py selects the store, migrates and verifies; cutover waits for the operator's Phase account. |
| TASK-022 | in-progress | high | M010 | [Edge migration: certificates, Caddy sites on Traefik, AdGuard as code](/tasks/task-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a) | Let's Encrypt wildcard on Traefik, the active Caddy sites as Traefik routes, then AdGuard rebuilt from code and the names moved from Caddy to the cluster. |
| TASK-030 | in-progress | medium | M013 | [NetBox as the full inventory: real hardware, ports, cables, guests and diagram plugins](/tasks/task-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues) | NetBox holds named hardware models, ports, hardware facts, the cables the switch announces and what every guest is, draws diagrams through plugins, and the roots check their plans against it. |
| TASK-035 | in-progress | medium | M010 | [Documentation maps: hub pages generated from the repository and a wiki with a curated sidebar](/tasks/task-035-documentation-maps-hub-pages-generated-from-the-repository-a) | docs/hubs holds one map per question, with tables and diagrams generated from the repository's own files; the Forgejo wiki opens on docs/home.md and lists the maps in its sidebar. |
| TASK-036 | in-progress | medium | M010 | [Media stack on pve-infra: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on a Compose VM](/tasks/task-036-media-stack-on-pve-infra-jellyfin-seerr-radarr-sonarr-prowla) | VM media-01 on pve-infra with Docker Compose: Jellyfin, Seerr, the Arr tools and qBittorrent; shared PostgreSQL, NAS read-only, a test area. |
| TASK-037 | in-progress | medium | M010 | [TrueNAS under management: metrics in Grafana, apps as code, housekeeping](/tasks/task-037-truenas-under-management-metrics-in-grafana-apps-as-code-hou) | The NAS's metrics and alerts in the monitoring stack, its apps described in the repository with a plan-before-apply path, and the leftovers of the old environment cleaned up |
| TASK-002 | planned | critical | M000 | [Live read-only inventory of Proxmox hosts, guests and storage](/tasks/task-002-live-proxmox-inventory) | Verify hosts, cluster membership, VMs/LXCs, storage and capacity on every node; correct the legacy inventory. |
| TASK-003 | planned | high | M010 | [Service dependency, network/DNS and data/backup map](/tasks/task-003-service-dependency-and-data-map) | Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage. |
| TASK-004 | planned | high | M012 | [Representative PBS restore test](/tasks/task-004-pbs-representative-restore) | Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data. |
| TASK-005 | planned | high | M010 | [Migration order and bootstrap credential requirements](/tasks/task-005-migration-order-and-bootstrap-credentials) | Decide the service migration order and list every bootstrap credential and recovery prerequisite. |
| TASK-011 | planned | critical | M012 | [SOPS + age bootstrap secrets](/tasks/task-011-sops-age-bootstrap-secrets) | Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows. |
| TASK-012 | planned | high | M012 | [Independent bootstrap and recovery runbook](/tasks/task-012-bootstrap-and-recovery-runbook) | Write and exercise the runbook that rebuilds the management VM from a clean workstation. |
| TASK-007 | completed | critical | M001 | [Scoped Proxmox API token and SSH access for pve-management](/tasks/task-007-pve-management-access) | Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible. |
| TASK-008 | completed | critical | M001 | [Reusable OpenTofu guest module and management VM root](/tasks/task-008-proxmox-guest-module-and-management-vm) | Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM. |
| TASK-009 | completed | high | M001 | [Ansible baseline for the management VM (toolchain and runner)](/tasks/task-009-management-vm-ansible-baseline) | Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008). |
| TASK-010 | completed | critical | M001 | [OpenTofu state: one local authority, handed over to the workstation](/tasks/task-010-state-management-and-backups) | Keep new-root state local on the single operator workstation, move it from the Mac to mgmt-control-01, and never let an empty state recreate existing guests. |
| TASK-013 | completed | critical | M002 | [Reinstall pve-core and form the new Proxmox cluster](/tasks/task-013-reinstall-pve-core-and-form-cluster) | Confirm the emptied pve-core holds nothing to keep, inventory its NVMe, reinstall Proxmox VE, create the cluster on pve-management and join pve-core with an explicit two-node quorum plan. |
| TASK-014 | completed | high | M003 | [Bootstrap deployment runner VM on pve-core](/tasks/task-014-bootstrap-deployment-runner-vm) | Runner VM deploy-runner-01 (VMID 302, .32) on pve-core via headless-vm, deploy_runner role, main-only wrapper, approval-gated dispatch workflow and a disposable proof root (ADR-014). |
| TASK-015 | completed | high | M004 | [k3s cluster on doku-lab: first server on pve-lab](/tasks/task-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab) | terraform/stacks/k3s VMs (for_each, rebuildable), k3s role with embedded etcd, token in Infisical /k3s, host keys pinned out-of-band, workstation kubeconfig (ADR-011). |
| TASK-016 | completed | high | M005 | [Headlamp on k3s with LAN-only ingress and token login](/tasks/task-016-headlamp-on-k3s-with-lan-only-ingress-and-token-login) | Official chart 0.46.0, no cluster rights for the app, admin ServiceAccount token in Infisical dev:/headlamp, HTTPS ingress limited to 192.168.0.0/24. |
| TASK-017 | completed | high | M006 | [Shared NFS storage VM on pve-core and nvme-shared StorageClass](/tasks/task-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla) | storage-01 (VM 350, .50, 300 GiB data disk) exports NFSv4 to the k3s nodes only; csi-driver-nfs 4.13.6 with a Retain class for user data; app data stays on local-path. |
| TASK-018 | completed | high | M007 | [PostgreSQL platform: three Patroni VMs outside k3s with a virtual IP](/tasks/task-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir) | Three Debian 13 VMs (pg-01..03 on pve-core, pve-lab, pve-infra) run PostgreSQL 17 under Patroni with etcd and a virtual IP; per-application databases and roles. |
| TASK-020 | completed | medium | M010 | [Lean observability: Prometheus, Loki, Grafana and Alloy](/tasks/task-020-lean-observability-prometheus-loki-grafana-and-alloy) | Prometheus, Loki and Grafana on k3s; Alloy collects a small allow-list of metrics and logs from the cluster and from every VM; Grafana state on the shared PostgreSQL. |
| TASK-021 | completed | medium | M004 | [k3s servers on pve-core and pve-lab: three etcd members](/tasks/task-021-k3s-servers-on-pve-core-and-pve-lab-three-etcd-members) | k3s-server-02 on pve-core and k3s-server-03 on pve-lab join the embedded etcd; Traefik runs on every node so ingress survives a reschedule. |
| TASK-023 | completed | medium | M013 | [NetBox on k3s, initial inventory, reconciliation and Ansible inventory](/tasks/task-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i) | Deploy NetBox with the official chart on the shared PostgreSQL, populate it from the OpenTofu outputs and read-only Proxmox discovery, and let Ansible read its inventory from it. |
| TASK-024 | completed | medium | M009 | [Argo CD on k3s and every service of the cluster under it](/tasks/task-024-argo-cd-on-k3s-and-netbox-as-its-first-application) | Install Argo CD, restrict it to this repository and named namespaces, and move every service of the cluster under it without a restart. |
| TASK-025 | completed | medium | M009 | [Windmill on k3s reading its data from NetBox](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox) | Deploy Windmill under Argo CD on the shared PostgreSQL, bootstrap it without default credentials, and publish scripts from Git that read roles, ranges and free addresses from NetBox. |
| TASK-026 | completed | medium | M014 | [Authentik on k3s and single sign-on for Argo CD, Grafana, NetBox and Windmill](/tasks/task-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb) | Authentik 2026.8.5 under Argo CD on the shared PostgreSQL; applications and groups as blueprints; OIDC sign-in wired for Argo CD, Grafana, NetBox and Windmill with local administrators kept. |
| TASK-027 | completed | medium | M010 | [Homepage on k3s behind Authentik, rearranged for the doku-lab cluster, with a new widget data API](/tasks/task-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab) | The dashboard moved from legacy CT201 to k3s under Argo CD, behind Authentik forward authentication, with cards for the new platform and a widget API fed by Proxmox, Prometheus and HTTP checks. |
| TASK-028 | completed | medium | M001 | [Workstation VM renders on the host's graphics adapter](/tasks/task-028-workstation-vm-renders-on-the-host-s-graphics-adapter) | VM 100 gets the Intel UHD 630 of pve-management through a resource mapping, all twelve host threads and Proxmox protection; cold start with automatic rollback. |
| TASK-029 | completed | medium | M010 | [Wiki.js 3 on k3s showing this repository's documentation](/tasks/task-029-wiki-js-3-on-k3s-showing-this-repository-s-documentation) | Wiki.js 3.5 on k3s under Argo CD with the shared PostgreSQL and Authentik sign-in; its pages are generated from this repository and pulled by the wiki's Git storage. |
| TASK-031 | completed | medium | M010 | [Switch port counters over SNMP in Prometheus and Grafana](/tasks/task-031-switch-port-counters-over-snmp-in-prometheus-and-grafana) | Alloy reads the QNAP switch's interface table over SNMPv3 every 15 seconds and pushes it to Prometheus; dashboard and four alerts; sign-in from the secret store. |
| TASK-032 | completed | medium | M010 | [Vaultwarden on k3s with its vault in the shared PostgreSQL](/tasks/task-032-vaultwarden-on-k3s-with-its-vault-in-the-shared-postgresql) | Vaultwarden moves from the container on the old host to k3s; its SQLite vault is copied into the shared PostgreSQL; same name, same account. |
| TASK-033 | completed | medium | M010 | [Clean CI runner ci-runner-01 on the new cluster, replacing CT301](/tasks/task-033-clean-ci-runner-ci-runner-01-on-the-new-cluster-replacing-ct) | One validation runner VM built by OpenTofu and Ansible serves every repository; the hand-grown CT301 on the old host is retired |
| TASK-034 | completed | medium | M010 | [VictoriaMetrics replaces Prometheus; vmalert evaluates the rules](/tasks/task-034-victoriametrics-replaces-prometheus-vmalert-evaluates-the-ru) | VictoriaMetrics single node stores the metrics Alloy pushes, vmalert evaluates the alert rules, kube-state-metrics is its own chart; Prometheus is retired |

## Decisions

| ID | Status | Title | Component | Summary |
|----|--------|-------|-----------|---------|
| ADR-001 | accepted | [Rolling infrastructure rebuild — the old infrastructure builds the new](/docs/decisions/adr-001-rolling-infrastructure-rebuild) | platform | Rebuild service by service using the running homelab to provision its replacement; no big-bang rebuild, no full hardware duplication. |
| ADR-002 | superseded | [pve-management is a standalone bootstrap, orchestration and recovery host](/docs/decisions/adr-002-pve-management-standalone-host) | pve-management | The fresh Proxmox host pve-management stays outside the compute cluster and runs only management VMs (IaC toolchain, runner, later Windmill/Phase). |
| ADR-003 | accepted | [OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually](/docs/decisions/adr-003-opentofu-for-new-infrastructure) | infrastructure | New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan. |
| ADR-004 | accepted | [Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap) | secrets | Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill. |
| ADR-005 | accepted | [Windmill is the operations UI over a versioned service catalog](/docs/decisions/adr-005-windmill-service-catalog) | orchestration | Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo. |
| ADR-006 | superseded | [Docker Compose first; k3s and Argo CD later, only where they add value](/docs/decisions/adr-006-compose-first-kubernetes-later) | application | Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction. |
| ADR-007 | accepted | [Archive the legacy Codex workflow; keep live legacy IaC roots in place until migrated](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots) | repository | Old AGENTS.md, roadmap, tasks and docs moved verbatim to docs/archive/codex-2026; legacy Terraform/Ansible code that still manages live resources stays at its path. |
| ADR-008 | accepted | [Bootstrap runs from the operator workstation; CT301 stays validation-only](/docs/decisions/adr-008-workstation-bootstrap-ct301-validation-only) | execution | The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later. |
| ADR-009 | accepted | [The management VM is the operator's GNOME admin workstation](/docs/decisions/adr-009-management-vm-gnome-admin-workstation) | pve-management | mgmt-control-01 is a GNOME admin workstation (Ubuntu 26.04, 8 vCPU host type, 10 GiB, 120 GiB) with RDP remote login, the IaC toolchain, Claude Code and Codex. |
| ADR-010 | accepted | [The new Proxmox cluster is founded on pve-management and grows with reclaimed hosts](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management) | proxmox | pve-management founds the new Proxmox cluster; the emptied pve-core joins first, every reclaimed host follows by the same repeatable process. Supersedes ADR-002. |
| ADR-011 | accepted | [k3s is the application platform from the start, reconciled by Argo CD and administered with Headlamp](/docs/decisions/adr-011-k3s-first-argocd-headlamp) | application | New applications run on k3s (OpenTofu VMs, Ansible bootstrap, embedded etcd); Argo CD reconciles them from Forgejo; Headlamp is the Kubernetes UI; Windmill automates workflows. Supersedes ADR-006. |
| ADR-012 | accepted | [Kubernetes persistent data lives on NVMe-backed storage outside k3s; TrueNAS is the backup destination; Ceph later](/docs/decisions/adr-012-external-nvme-storage-truenas-backups) | storage | PVCs come through CSI from NVMe-backed storage outside k3s on the physical hosts; TrueNAS only receives backups; Ceph (RBD, CephFS) is the future distributed layer. |
| ADR-013 | accepted | [A central PostgreSQL platform with Patroni replication serves the applications](/docs/decisions/adr-013-central-postgresql-patroni) | database | Applications get their own database, role and credentials on a shared PostgreSQL platform managed by Patroni (Zalando Postgres Operator pending validation), on external NVMe-backed PVCs. |
| ADR-014 | accepted | [A dedicated Forgejo runner VM executes approved infrastructure workflows](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner) | execution | A runner VM created with OpenTofu and configured with Ansible runs approved OpenTofu, Ansible, k3s and Helm jobs with scoped credentials; CT301 stays validation-only. Amends ADR-008. |
| ADR-015 | accepted | [PostgreSQL runs on three Patroni VMs outside k3s](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s) | database | Operator decision 2026-11-17: the shared PostgreSQL platform is three Patroni VMs outside k3s with etcd and a virtual IP, not an operator inside k3s. |
| ADR-016 | accepted | [NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f) | inventory | NetBox on k3s holds the intended inventory and address plan; Git owns what OpenTofu defines, Proxmox is only observed, NetBox is never a bootstrap dependency. |
| ADR-017 | accepted | [Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency](/docs/decisions/adr-017-authentik-is-the-single-sign-on-of-the-platform-declared-in) | identity | Authentik on k3s signs people in to the web interfaces; applications and groups are blueprints in Git, people live in Authentik, and each service keeps a local administrator. |
| ADR-018 | accepted | [NetBox holds the physical inventory: Git says what a device is, machines report their hardware, people place it](/docs/decisions/adr-018-netbox-holds-the-physical-inventory-git-says-what-a-device-i) | netbox | Device identity comes from inventory.yaml, hardware and cabling from what hosts and the switch report, placement stays with people in NetBox; diagram plugins are installed on a volume. |

## External references

### NetBox

| ID | Type | Status | Version | Title |
|----|------|--------|---------|-------|
| REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll | api-reference | current | NetBox 4.7.5, chart netbox 8.3.107, netbox.netbox 3.24.0 | [NetBox 4.7 REST API, chart 8.3.107 and the netbox.netbox collection](/docs/reference/external/netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll) |

### Wiki.js

| ID | Type | Status | Version | Title |
|----|------|--------|---------|-------|
| REF-wiki-js-3-4-requirements-container-settings-and-migration-fr | library-reference | current | 3.4.0 | [Wiki.js 3.4: requirements, container settings and migration from 2.x](/docs/reference/external/wiki-js-3-4-requirements-container-settings-and-migration-fr) |

## Documents by type

### Project overview

- **DOC-project-overview** [homelab-iac — project vision and overview](/docs/project-overview) (current) `overview, vision, rebuild, status` — Authoritative vision, rolling-rebuild strategy, target stack and roadmap M000-M012, current status, confirmed decisions vs pending technical choices; read first.

### Architecture

- **ARCH-platform** [Target homelab platform architecture](/docs/architecture/platform) (current) — platform `architecture, platform, rebuild` — Layers and owners of the rebuilt homelab: Proxmox cluster, k3s, Headlamp, external NVMe storage via CSI, PostgreSQL/Patroni, Phase, Argo CD, Windmill, runner; TrueNAS for backups.

### Investigation result

- **INV-legacy-inventory** [Legacy homelab inventory (archived repository, operator corrections, state review)](/docs/investigations/legacy-inventory) (needs-review) — inventory `investigation, inventory, legacy` — Legacy hosts, guests, services and local Terraform states, with retired hosts, stale state and endpoint hazards; starting point for the M000 live inventory.
- **INV-new-proxmox-cluster-inventory** [New Proxmox cluster inventory](/docs/investigations/new-proxmox-cluster-inventory) (current) `investigation, inventory, proxmox, cluster, hardware` — Authoritative read-only audit of the new doku-lab cluster (pve-management, pve-core, pve-infra, new pve-lab .16): membership, hardware, NVMe, network, guests, capacity, placement.
- **INV-pve-management-bootstrap** [pve-management bootstrap — readiness and implementation plan](/docs/investigations/pve-management-bootstrap) (current) — pve-management `investigation, bootstrap, pve-management, plan` — Readiness, exact API privileges, SSH/TLS/state decisions, proposed VM values and the next step for provisioning mgmt-control-01 on pve-management; nothing applied.

### Known issue

- **ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte** [Bursts of full-size frames are lost on the way into the Intel I219 hosts](/docs/issues/bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte) (open) — network `issue, network, proxmox` — pve-core and pve-management lose 3 to 5 % of back-to-back full-size frames they receive; TCP from faster hosts falls to 20-60 Mbit/s. Cause not fixed yet.

### Guide

- **GUIDE-handoff** [Current handoff and next steps](/docs/handoff) (current) `guide, handoff, workstation, pve-management` — Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task.
- **GUIDE-home** [homelab-iac](/docs/home) (current) `map, home` — Entry page of the documentation: what the platform is, the cluster at a glance and the maps that answer one question each.
- **GUIDE-map-architecture** [Architecture map](/docs/hubs/architecture-map) (current) `map, architecture` — How the pieces fit: the layers from the hardware to the applications, and which tool owns which concern.
- **GUIDE-map-ci-cd** [CI/CD map](/docs/hubs/ci-cd-map) (current) `map, ci, forgejo` — The Forgejo workflows, what starts them, which runner executes them and the checks they run.
- **GUIDE-map-decisions** [Architecture decisions](/docs/hubs/architecture-decisions) (current) `map, decisions` — Every decision record, its status and what it replaced.
- **GUIDE-map-dependencies** [Dependency map](/docs/hubs/dependency-map) (current) `map, dependencies, bootstrap` — What needs what to run, the order in which the platform starts, and the order in which it was built.
- **GUIDE-map-deployment** [Deployment map](/docs/hubs/deployment-map) (current) `map, deployment, opentofu, ansible, argocd` — What deploys what: the OpenTofu root of each guest, the playbook that configures it and the Argo CD application of each service.
- **GUIDE-map-history** [Development history](/docs/hubs/development-history) (current) `map, roadmap, history` — Milestones, the tasks under each and what is open now.
- **GUIDE-map-identity** [Identity and secrets map](/docs/hubs/identity-and-secrets-map) (current) `map, identity, secrets, authentik, phase` — Who signs in where and through what, and which secret-store path feeds which deployment.
- **GUIDE-map-infrastructure** [Infrastructure map](/docs/hubs/infrastructure-map) (current) `map, infrastructure, proxmox` — Hosts, guests and how they are wired: which machine runs what, with its size and address.
- **GUIDE-map-network** [Network and names](/docs/hubs/network-map) (current) `map, network, dns, ingress` — Which name answers where: the LAN's DNS answers, the shared addresses and the route behind each name.
- **GUIDE-map-operations** [Operations](/docs/hubs/operations) (current) `map, operations` — Day-to-day procedures: where the commands are, how to take a host down, what is known to be broken.
- **GUIDE-map-services** [Service catalog](/docs/hubs/service-catalog) (current) `map, services, k3s` — Every service of the platform: its site, where it runs, what signs people in and where its data lives.
- **GUIDE-media-stack** [Media stack: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on media-01](/docs/guides/media-stack) (current) `guide, media, jellyfin, docker-compose` — What runs on media-01, where its data lives, how to operate, test, back up and restore it, and how to give it the NAS library.

### Project reference

- **DOC-infrastructure-inventory** [Infrastructure inventory](/docs/reference/infrastructure-inventory) (current) `reference, netbox, inventory, hardware, network` — Devices, cabling, networks, addresses and virtual machines of the homelab, generated from NetBox: change NetBox or services/netbox/inventory.yaml, not this page.

## Implementation history

_No commit records. Generate with `harness history sync`._

## By tag

- **access**: TASK-007
- **adguard**: TASK-022
- **age**: ADR-004, TASK-011
- **alloy**: TASK-020
- **ansible**: GUIDE-map-deployment, TASK-009, TASK-014, TASK-015, TASK-017, TASK-018
- **architecture**: ARCH-platform, GUIDE-map-architecture
- **archive**: ADR-007
- **argocd**: ADR-006, ADR-011, GUIDE-map-deployment, TASK-024, TASK-026
- **authentication**: ADR-017
- **authentik**: ADR-017, GUIDE-map-identity, M014, TASK-026, TASK-027, TASK-029
- **automation**: TASK-025
- **backup**: ADR-012, TASK-003, TASK-004, TASK-010
- **bootstrap**: ADR-002, ADR-008, GUIDE-map-dependencies, INV-pve-management-bootstrap, M001
- **caddy**: TASK-022
- **ceph**: ADR-012
- **cert-manager**: TASK-022
- **ci**: ADR-008, ADR-014, GUIDE-map-ci-cd, TASK-014, TASK-033
- **cluster**: ADR-010, INV-new-proxmox-cluster-inventory, TASK-013
- **compose**: ADR-006
- **compute**: TASK-013
- **csi**: ADR-012
- **dashboard**: TASK-027
- **database**: ADR-013, ADR-015
- **decision**: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017
- **decisions**: GUIDE-map-decisions
- **dependencies**: GUIDE-map-dependencies, TASK-003
- **deployment**: ADR-014, GUIDE-map-deployment
- **desktop**: ADR-009
- **dns**: GUIDE-map-network, TASK-022
- **docker-compose**: GUIDE-media-stack, TASK-036
- **documentation**: TASK-029, TASK-035
- **etcd**: TASK-018, TASK-021
- **external**: REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll, REF-wiki-js-3-4-requirements-container-settings-and-migration-fr
- **flux**: ADR-006
- **forgejo**: ADR-014, GUIDE-map-ci-cd, TASK-014
- **forward-auth**: TASK-027
- **gitops**: ADR-005, TASK-024
- **gpu**: TASK-028
- **grafana**: TASK-020, TASK-026
- **guide**: GUIDE-handoff, GUIDE-media-stack
- **handoff**: GUIDE-handoff
- **hardware**: ADR-018, DOC-infrastructure-inventory, INV-new-proxmox-cluster-inventory, TASK-030
- **harness**: TASK-001
- **headlamp**: ADR-011, TASK-016
- **history**: GUIDE-map-history
- **home**: GUIDE-home
- **homepage**: TASK-027
- **identity**: GUIDE-map-identity
- **infisical**: ADR-004, TASK-019
- **infrastructure**: GUIDE-map-infrastructure
- **ingress**: GUIDE-map-network, TASK-022
- **inventory**: ADR-016, ADR-018, DOC-infrastructure-inventory, INV-legacy-inventory, INV-new-proxmox-cluster-inventory, M000, M013, TASK-002, TASK-003, TASK-023, TASK-030
- **investigation**: INV-legacy-inventory, INV-new-proxmox-cluster-inventory, INV-pve-management-bootstrap
- **ipam**: ADR-016, TASK-023
- **issue**: ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte
- **jellyfin**: GUIDE-media-stack, TASK-036
- **k3s**: ADR-006, ADR-011, GUIDE-map-services, TASK-015, TASK-016, TASK-017, TASK-019, TASK-021
- **kubernetes**: ADR-006, ADR-011
- **layout**: TASK-006
- **legacy**: ADR-007, INV-legacy-inventory
- **loki**: TASK-020
- **m002**: TASK-013
- **make**: TASK-006
- **management**: ADR-002, ADR-009
- **map**: GUIDE-home, GUIDE-map-architecture, GUIDE-map-ci-cd, GUIDE-map-decisions, GUIDE-map-dependencies, GUIDE-map-deployment, GUIDE-map-history, GUIDE-map-identity, GUIDE-map-infrastructure, GUIDE-map-network, GUIDE-map-operations, GUIDE-map-services
- **maps**: TASK-035
- **media**: GUIDE-media-stack, TASK-036
- **migration**: ADR-001, REF-wiki-js-3-4-requirements-container-settings-and-migration-fr, TASK-005, TASK-019, TASK-027, TASK-029, TASK-032, TASK-033
- **monitoring**: TASK-037
- **netbox**: ADR-016, ADR-018, DOC-infrastructure-inventory, M013, REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll, TASK-023, TASK-025, TASK-026, TASK-030
- **network**: DOC-infrastructure-inventory, GUIDE-map-network, ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte, TASK-031
- **nfs**: TASK-017
- **nvme**: ADR-012
- **observability**: TASK-020, TASK-031, TASK-034
- **opentofu**: ADR-003, GUIDE-map-deployment, TASK-006, TASK-008, TASK-014, TASK-015, TASK-017, TASK-018
- **operations**: GUIDE-map-operations
- **overview**: DOC-project-overview
- **patroni**: ADR-013, ADR-015, TASK-018
- **pbs**: TASK-004
- **performance**: TASK-028
- **phase**: ADR-004, GUIDE-map-identity, TASK-019
- **plan**: INV-pve-management-bootstrap
- **planning**: M000, TASK-005
- **platform**: ARCH-platform
- **postgresql**: ADR-013, ADR-015, TASK-018
- **prometheus**: TASK-020
- **proxmox**: ADR-002, ADR-010, GUIDE-map-infrastructure, INV-new-proxmox-cluster-inventory, ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte, TASK-002, TASK-013, TASK-021, TASK-028
- **pve-core**: ADR-010, TASK-013
- **pve-management**: ADR-009, ADR-010, GUIDE-handoff, INV-pve-management-bootstrap, M001, TASK-007, TASK-008
- **rebuild**: ARCH-platform, DOC-project-overview
- **recovery**: TASK-004, TASK-012
- **reference**: DOC-infrastructure-inventory, REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll, REF-wiki-js-3-4-requirements-container-settings-and-migration-fr
- **repository**: TASK-001
- **roadmap**: GUIDE-map-history, M002, M003, M004, M005, M006, M007, M008, M009, M010, M011, M012, M013, M014
- **runbook**: TASK-012
- **runner**: ADR-008, ADR-014, TASK-009, TASK-014, TASK-033
- **secrets**: ADR-004, GUIDE-map-identity, TASK-011, TASK-019
- **security**: ADR-008
- **service-catalog**: ADR-005
- **services**: GUIDE-map-services
- **sops**: ADR-004, TASK-011
- **sso**: ADR-017, M014, TASK-026
- **state**: ADR-007, TASK-010
- **status**: DOC-project-overview
- **storage**: ADR-012, TASK-017
- **strategy**: ADR-001
- **terraform**: ADR-003
- **traefik**: TASK-021, TASK-022
- **truenas**: ADR-012, TASK-037
- **vaultwarden**: TASK-032
- **victoriametrics**: TASK-034
- **vision**: DOC-project-overview
- **wiki**: REF-wiki-js-3-4-requirements-container-settings-and-migration-fr, TASK-029, TASK-035
- **windmill**: ADR-005, ADR-011, TASK-025, TASK-026
- **workstation**: ADR-009, GUIDE-handoff, TASK-028

## By component

- **application**: ADR-006, ADR-011
- **database**: ADR-013, ADR-015
- **execution**: ADR-008, ADR-014
- **identity**: ADR-017
- **infrastructure**: ADR-003
- **inventory**: ADR-016, INV-legacy-inventory
- **netbox**: ADR-018
- **network**: ISSUE-bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte
- **orchestration**: ADR-005
- **platform**: ADR-001, ARCH-platform
- **proxmox**: ADR-010
- **pve-management**: ADR-002, ADR-009, INV-pve-management-bootstrap
- **repository**: ADR-007
- **secrets**: ADR-004
- **storage**: ADR-012

## By technology

- **NetBox**: REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll
- **Wiki.js**: REF-wiki-js-3-4-requirements-container-settings-and-migration-fr

## Broken references

_None._
