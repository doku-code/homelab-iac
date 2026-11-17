---
id: INDEX-knowledge-map
title: Knowledge map
type: index
status: generated
generated: true
generator: harness docs index
tags: [index]
---

# Knowledge map

Generated navigation index. Do not edit; regenerate with `harness docs index`.
Documents are the source of truth; this map only lists them.

How to use: find the row that matches your task (by type, tag, component or ID), open only that document, then follow its `related*` links. Use `harness docs search <terms>` for anything not visible here.

## Milestones

| ID | Status | Priority | Title | Tasks | Summary |
|----|--------|----------|-------|-------|---------|
| M000 | active | critical | [Infrastructure inventory and migration planning](../milestones/M000-inventory-and-migration-planning.md) | in-progress: 1, planned: 1 | Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime. |
| M003 | active | high | [Dedicated Forgejo deployment runner](../milestones/M003-deployment-runner.md) | in-progress: 1 | A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials. |
| M004 | planned | high | [k3s bootstrap](../milestones/M004-k3s-bootstrap.md) | none | The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl. |
| M005 | planned | high | [Headlamp](../milestones/M005-headlamp.md) | none | Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs. |
| M006 | planned | high | [External NVMe-backed storage](../milestones/M006-external-nvme-storage.md) | none | Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented. |
| M007 | planned | high | [PostgreSQL platform](../milestones/M007-postgresql-platform.md) | none | The selected PostgreSQL operator runs a Patroni-managed primary on external NVMe-backed storage, with per-application databases and roles. |
| M008 | planned | high | [Phase](../milestones/M008-phase.md) | none | Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it. |
| M009 | planned | medium | [Argo CD and Windmill](../milestones/M009-argocd-windmill.md) | none | Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner. |
| M010 | planned | high | [Rolling application migration](../milestones/M010-rolling-application-migration.md) | planned: 2 | Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster. |
| M011 | planned | medium | [Ceph and infrastructure expansion](../milestones/M011-ceph-and-expansion.md) | none | With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts. |
| M012 | planned | medium | [Backups and finalization](../milestones/M012-backups-and-finalization.md) | planned: 3 | Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired. |
| M001 | completed | critical | [Management workstation](../milestones/M001-bootstrap-pve-management.md) | completed: 4, in-progress: 1 | Existing infrastructure provisions and configures the management workstation VM on pve-management from IaC, and operations move to it. |
| M002 | completed | critical | [New Proxmox cluster (four nodes)](../milestones/M002-proxmox-compute-capacity.md) | completed: 1 | The new cluster doku-lab runs on pve-management, pve-core, pve-infra and the new pve-lab (.16), quorate, with its hardware and capacity inventoried. |

## Tasks

| ID | Status | Priority | Milestone | Title | Summary |
|----|--------|----------|-----------|-------|---------|
| TASK-001 | in-progress | critical | M000 | [Reset repository to the agent harness and record the rebuild direction](../tasks/TASK-001-repository-reset-and-alignment.md) | Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap. |
| TASK-006 | in-progress | critical | M001 | [Target repository layout, OpenTofu toolchain and management Make targets](../tasks/TASK-006-target-layout-and-service-contract.md) | Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check). |
| TASK-014 | in-progress | high | M003 | [Bootstrap deployment runner VM on pve-core](../tasks/TASK-014-bootstrap-deployment-runner-vm.md) | Runner VM deploy-runner-01 (VMID 302, .32) on pve-core via headless-vm, deploy_runner role, main-only wrapper, approval-gated dispatch workflow and a disposable proof root (ADR-014). |
| TASK-002 | planned | critical | M000 | [Live read-only inventory of Proxmox hosts, guests and storage](../tasks/TASK-002-live-proxmox-inventory.md) | Verify hosts, cluster membership, VMs/LXCs, storage and capacity on every node; correct the legacy inventory. |
| TASK-003 | planned | high | M010 | [Service dependency, network/DNS and data/backup map](../tasks/TASK-003-service-dependency-and-data-map.md) | Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage. |
| TASK-004 | planned | high | M012 | [Representative PBS restore test](../tasks/TASK-004-pbs-representative-restore.md) | Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data. |
| TASK-005 | planned | high | M010 | [Migration order and bootstrap credential requirements](../tasks/TASK-005-migration-order-and-bootstrap-credentials.md) | Decide the service migration order and list every bootstrap credential and recovery prerequisite. |
| TASK-011 | planned | critical | M012 | [SOPS + age bootstrap secrets](../tasks/TASK-011-sops-age-bootstrap-secrets.md) | Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows. |
| TASK-012 | planned | high | M012 | [Independent bootstrap and recovery runbook](../tasks/TASK-012-bootstrap-and-recovery-runbook.md) | Write and exercise the runbook that rebuilds the management VM from a clean workstation. |
| TASK-007 | completed | critical | M001 | [Scoped Proxmox API token and SSH access for pve-management](../tasks/TASK-007-pve-management-access.md) | Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible. |
| TASK-008 | completed | critical | M001 | [Reusable OpenTofu guest module and management VM root](../tasks/TASK-008-proxmox-guest-module-and-management-vm.md) | Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM. |
| TASK-009 | completed | high | M001 | [Ansible baseline for the management VM (toolchain and runner)](../tasks/TASK-009-management-vm-ansible-baseline.md) | Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008). |
| TASK-010 | completed | critical | M001 | [OpenTofu state: one local authority, handed over to the workstation](../tasks/TASK-010-state-management-and-backups.md) | Keep new-root state local on the single operator workstation, move it from the Mac to mgmt-control-01, and never let an empty state recreate existing guests. |
| TASK-013 | completed | critical | M002 | [Reinstall pve-core and form the new Proxmox cluster](../tasks/TASK-013-reinstall-pve-core-and-form-cluster.md) | Confirm the emptied pve-core holds nothing to keep, inventory its NVMe, reinstall Proxmox VE, create the cluster on pve-management and join pve-core with an explicit two-node quorum plan. |

## Decisions

| ID | Status | Title | Component | Summary |
|----|--------|-------|-----------|---------|
| ADR-001 | accepted | [Rolling infrastructure rebuild — the old infrastructure builds the new](decisions/ADR-001-rolling-infrastructure-rebuild.md) | platform | Rebuild service by service using the running homelab to provision its replacement; no big-bang rebuild, no full hardware duplication. |
| ADR-002 | superseded | [pve-management is a standalone bootstrap, orchestration and recovery host](decisions/ADR-002-pve-management-standalone-host.md) | pve-management | The fresh Proxmox host pve-management stays outside the compute cluster and runs only management VMs (IaC toolchain, runner, later Windmill/Phase). |
| ADR-003 | accepted | [OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually](decisions/ADR-003-opentofu-for-new-infrastructure.md) | infrastructure | New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan. |
| ADR-004 | accepted | [Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets](decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md) | secrets | Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill. |
| ADR-005 | accepted | [Windmill is the operations UI over a versioned service catalog](decisions/ADR-005-windmill-service-catalog.md) | orchestration | Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo. |
| ADR-006 | superseded | [Docker Compose first; k3s and Argo CD later, only where they add value](decisions/ADR-006-compose-first-kubernetes-later.md) | application | Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction. |
| ADR-007 | accepted | [Archive the legacy Codex workflow; keep live legacy IaC roots in place until migrated](decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md) | repository | Old AGENTS.md, roadmap, tasks and docs moved verbatim to docs/archive/codex-2026; legacy Terraform/Ansible code that still manages live resources stays at its path. |
| ADR-008 | accepted | [Bootstrap runs from the operator workstation; CT301 stays validation-only](decisions/ADR-008-workstation-bootstrap-ct301-validation-only.md) | execution | The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later. |
| ADR-009 | accepted | [The management VM is the operator's GNOME admin workstation](decisions/ADR-009-management-vm-gnome-admin-workstation.md) | pve-management | mgmt-control-01 is a GNOME admin workstation (Ubuntu 26.04, 8 vCPU host type, 10 GiB, 120 GiB) with RDP remote login, the IaC toolchain, Claude Code and Codex. |
| ADR-010 | accepted | [The new Proxmox cluster is founded on pve-management and grows with reclaimed hosts](decisions/ADR-010-new-proxmox-cluster-on-pve-management.md) | proxmox | pve-management founds the new Proxmox cluster; the emptied pve-core joins first, every reclaimed host follows by the same repeatable process. Supersedes ADR-002. |
| ADR-011 | accepted | [k3s is the application platform from the start, reconciled by Argo CD and administered with Headlamp](decisions/ADR-011-k3s-first-argocd-headlamp.md) | application | New applications run on k3s (OpenTofu VMs, Ansible bootstrap, embedded etcd); Argo CD reconciles them from Forgejo; Headlamp is the Kubernetes UI; Windmill automates workflows. Supersedes ADR-006. |
| ADR-012 | accepted | [Kubernetes persistent data lives on NVMe-backed storage outside k3s; TrueNAS is the backup destination; Ceph later](decisions/ADR-012-external-nvme-storage-truenas-backups.md) | storage | PVCs come through CSI from NVMe-backed storage outside k3s on the physical hosts; TrueNAS only receives backups; Ceph (RBD, CephFS) is the future distributed layer. |
| ADR-013 | accepted | [A central PostgreSQL platform with Patroni replication serves the applications](decisions/ADR-013-central-postgresql-patroni.md) | database | Applications get their own database, role and credentials on a shared PostgreSQL platform managed by Patroni (Zalando Postgres Operator pending validation), on external NVMe-backed PVCs. |
| ADR-014 | accepted | [A dedicated Forgejo runner VM executes approved infrastructure workflows](decisions/ADR-014-dedicated-forgejo-deployment-runner.md) | execution | A runner VM created with OpenTofu and configured with Ansible runs approved OpenTofu, Ansible, k3s and Helm jobs with scoped credentials; CT301 stays validation-only. Amends ADR-008. |

## External references

_No external references captured yet. Create one with `harness new api-reference`._

## Documents by type

### Project overview

- **DOC-project-overview** [homelab-iac — project vision and overview](project-overview.md) (current) `overview, vision, rebuild, status` — Authoritative vision, rolling-rebuild strategy, target stack and roadmap M000-M012, current status, confirmed decisions vs pending technical choices; read first.

### Architecture

- **ARCH-platform** [Target homelab platform architecture](architecture/platform.md) (current) — platform `architecture, platform, rebuild` — Layers and owners of the rebuilt homelab: Proxmox cluster, k3s, Headlamp, external NVMe storage via CSI, PostgreSQL/Patroni, Phase, Argo CD, Windmill, runner; TrueNAS for backups.

### Investigation result

- **INV-legacy-inventory** [Legacy homelab inventory (archived repository, operator corrections, state review)](investigations/legacy-inventory.md) (needs-review) — inventory `investigation, inventory, legacy` — Legacy hosts, guests, services and local Terraform states, with retired hosts, stale state and endpoint hazards; starting point for the M000 live inventory.
- **INV-new-proxmox-cluster-inventory** [New Proxmox cluster inventory](investigations/new-proxmox-cluster-inventory.md) (current) `investigation, inventory, proxmox, cluster, hardware` — Authoritative read-only audit of the new doku-lab cluster (pve-management, pve-core, pve-infra, new pve-lab .16): membership, hardware, NVMe, network, guests, capacity, placement.
- **INV-pve-management-bootstrap** [pve-management bootstrap — readiness and implementation plan](investigations/pve-management-bootstrap.md) (current) — pve-management `investigation, bootstrap, pve-management, plan` — Readiness, exact API privileges, SSH/TLS/state decisions, proposed VM values and the next step for provisioning mgmt-control-01 on pve-management; nothing applied.

### Guide

- **GUIDE-handoff** [Current handoff and next steps](handoff.md) (current) `guide, handoff, workstation, pve-management` — Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task.

## Implementation history

_No commit records. Generate with `harness history sync`._

## By tag

- **access**: TASK-007
- **age**: ADR-004, TASK-011
- **ansible**: TASK-009, TASK-014
- **architecture**: ARCH-platform
- **archive**: ADR-007
- **argocd**: ADR-006, ADR-011
- **backup**: ADR-012, TASK-003, TASK-004, TASK-010
- **bootstrap**: ADR-002, ADR-008, INV-pve-management-bootstrap, M001
- **ceph**: ADR-012
- **ci**: ADR-008, ADR-014, TASK-014
- **cluster**: ADR-010, INV-new-proxmox-cluster-inventory, TASK-013
- **compose**: ADR-006
- **compute**: TASK-013
- **csi**: ADR-012
- **database**: ADR-013
- **decision**: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014
- **dependencies**: TASK-003
- **deployment**: ADR-014
- **desktop**: ADR-009
- **flux**: ADR-006
- **forgejo**: ADR-014, TASK-014
- **gitops**: ADR-005
- **guide**: GUIDE-handoff
- **handoff**: GUIDE-handoff
- **hardware**: INV-new-proxmox-cluster-inventory
- **harness**: TASK-001
- **headlamp**: ADR-011
- **infisical**: ADR-004
- **inventory**: INV-legacy-inventory, INV-new-proxmox-cluster-inventory, M000, TASK-002, TASK-003
- **investigation**: INV-legacy-inventory, INV-new-proxmox-cluster-inventory, INV-pve-management-bootstrap
- **k3s**: ADR-006, ADR-011
- **kubernetes**: ADR-006, ADR-011
- **layout**: TASK-006
- **legacy**: ADR-007, INV-legacy-inventory
- **m002**: TASK-013
- **make**: TASK-006
- **management**: ADR-002, ADR-009
- **migration**: ADR-001, TASK-005
- **nvme**: ADR-012
- **opentofu**: ADR-003, TASK-006, TASK-008, TASK-014
- **overview**: DOC-project-overview
- **patroni**: ADR-013
- **pbs**: TASK-004
- **phase**: ADR-004
- **plan**: INV-pve-management-bootstrap
- **planning**: M000, TASK-005
- **platform**: ARCH-platform
- **postgresql**: ADR-013
- **proxmox**: ADR-002, ADR-010, INV-new-proxmox-cluster-inventory, TASK-002, TASK-013
- **pve-core**: ADR-010, TASK-013
- **pve-management**: ADR-009, ADR-010, GUIDE-handoff, INV-pve-management-bootstrap, M001, TASK-007, TASK-008
- **rebuild**: ARCH-platform, DOC-project-overview
- **recovery**: TASK-004, TASK-012
- **repository**: TASK-001
- **roadmap**: M002, M003, M004, M005, M006, M007, M008, M009, M010, M011, M012
- **runbook**: TASK-012
- **runner**: ADR-008, ADR-014, TASK-009, TASK-014
- **secrets**: ADR-004, TASK-011
- **security**: ADR-008
- **service-catalog**: ADR-005
- **sops**: ADR-004, TASK-011
- **state**: ADR-007, TASK-010
- **status**: DOC-project-overview
- **storage**: ADR-012
- **strategy**: ADR-001
- **terraform**: ADR-003
- **truenas**: ADR-012
- **vision**: DOC-project-overview
- **windmill**: ADR-005, ADR-011
- **workstation**: ADR-009, GUIDE-handoff

## By component

- **application**: ADR-006, ADR-011
- **database**: ADR-013
- **execution**: ADR-008, ADR-014
- **infrastructure**: ADR-003
- **inventory**: INV-legacy-inventory
- **orchestration**: ADR-005
- **platform**: ADR-001, ARCH-platform
- **proxmox**: ADR-010
- **pve-management**: ADR-002, ADR-009, INV-pve-management-bootstrap
- **repository**: ADR-007
- **secrets**: ADR-004
- **storage**: ADR-012

## By technology

_No technology recorded._

## Broken references

_None._
