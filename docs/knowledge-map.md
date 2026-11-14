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
| M000 | active | critical | [Infrastructure inventory and migration planning](../milestones/M000-inventory-and-migration-planning.md) | in-progress: 1, planned: 4 | Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime. |
| M001 | active | critical | [Bootstrap pve-management](../milestones/M001-bootstrap-pve-management.md) | completed: 1, in-progress: 4, planned: 2 | Existing infrastructure provisions and configures a management VM on pve-management automatically, with recoverable state and bootstrap secrets. |
| M002 | planned | high | [Secrets infrastructure (Phase)](../milestones/M002-secrets-infrastructure.md) | none | Phase deployed, recoverable independently, and used by deployment automation; controlled migration from Infisical begins. |
| M003 | planned | high | [Workflow automation (Windmill)](../milestones/M003-workflow-automation.md) | none | A Windmill workflow initiates an approved IaC operation from a service-catalog form and reports its outcome. |
| M004 | planned | high | [New compute infrastructure](../milestones/M004-new-compute-infrastructure.md) | none | The new compute environment can reliably host and restore migrated applications. |
| M005 | planned | high | [Rolling application migration](../milestones/M005-rolling-application-migration.md) | none | Existing services are progressively replaced without a complete homelab outage; emptied hosts are reinstalled and joined. |
| M006 | planned | medium | [Observability and platform improvements](../milestones/M006-observability.md) | none | Prometheus, Loki and Grafana give useful health checks, dashboards, logs and alerts, outside the bootstrap path. |
| M007 | planned | medium | [Core service cutover and retirement](../milestones/M007-core-service-cutover.md) | none | Foundational services run on the new platform, recovery works without the original cluster, and the old environment is decommissioned. |
| M008 | planned | low | [Advanced capabilities (future)](../milestones/M008-advanced-capabilities.md) | none | Future evaluation: k3s + Argo CD, self-service deployment forms and service catalog, automated node reinstallation, advanced DR. |

## Tasks

| ID | Status | Priority | Milestone | Title | Summary |
|----|--------|----------|-----------|-------|---------|
| TASK-001 | in-progress | critical | M000 | [Reset repository to the agent harness and record the rebuild direction](../tasks/TASK-001-repository-reset-and-alignment.md) | Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap. |
| TASK-006 | in-progress | critical | M001 | [Target repository layout, OpenTofu toolchain and management Make targets](../tasks/TASK-006-target-layout-and-service-contract.md) | Keep the terraform/ tree, pin OpenTofu 1.13.9 for new roots, add guarded mgmt-* Make targets and offline CI validation (make mgmt-check). |
| TASK-008 | in-progress | critical | M001 | [Reusable OpenTofu guest module and management VM root](../tasks/TASK-008-proxmox-guest-module-and-management-vm.md) | Write modules/opentofu/proxmox-guest (bpg/proxmox, cloud-init) and the stacks/management root that creates the Ubuntu management VM. |
| TASK-009 | in-progress | high | M001 | [Ansible baseline for the management VM (toolchain and runner)](../tasks/TASK-009-management-vm-ansible-baseline.md) | Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008). |
| TASK-010 | in-progress | critical | M001 | [OpenTofu state management and backups](../tasks/TASK-010-state-management-and-backups.md) | Choose the state backend for new roots and back up the existing legacy local states outside the operator workstation. |
| TASK-002 | planned | critical | M000 | [Live read-only inventory of Proxmox hosts, guests and storage](../tasks/TASK-002-live-proxmox-inventory.md) | Verify hosts, cluster membership, VMs/LXCs, storage and capacity on every node; correct the legacy inventory. |
| TASK-003 | planned | high | M000 | [Service dependency, network/DNS and data/backup map](../tasks/TASK-003-service-dependency-and-data-map.md) | Map every service's dependencies (DNS, proxy, auth, secrets, storage), its persistent data and its backup coverage. |
| TASK-004 | planned | high | M000 | [Representative PBS restore test](../tasks/TASK-004-pbs-representative-restore.md) | Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data. |
| TASK-005 | planned | high | M000 | [Migration order and bootstrap credential requirements](../tasks/TASK-005-migration-order-and-bootstrap-credentials.md) | Decide the service migration order and list every bootstrap credential and recovery prerequisite. |
| TASK-011 | planned | critical | M001 | [SOPS + age bootstrap secrets](../tasks/TASK-011-sops-age-bootstrap-secrets.md) | Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows. |
| TASK-012 | planned | high | M001 | [Independent bootstrap and recovery runbook](../tasks/TASK-012-bootstrap-and-recovery-runbook.md) | Write and exercise the runbook that rebuilds the management VM from a clean workstation. |
| TASK-007 | completed | critical | M001 | [Scoped Proxmox API token and SSH access for pve-management](../tasks/TASK-007-pve-management-access.md) | Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible. |

## Decisions

| ID | Status | Title | Component | Summary |
|----|--------|-------|-----------|---------|
| ADR-001 | accepted | [Rolling infrastructure rebuild — the old infrastructure builds the new](decisions/ADR-001-rolling-infrastructure-rebuild.md) | platform | Rebuild service by service using the running homelab to provision its replacement; no big-bang rebuild, no full hardware duplication. |
| ADR-002 | accepted | [pve-management is a standalone bootstrap, orchestration and recovery host](decisions/ADR-002-pve-management-standalone-host.md) | pve-management | The fresh Proxmox host pve-management stays outside the compute cluster and runs only management VMs (IaC toolchain, runner, later Windmill/Phase). |
| ADR-003 | accepted | [OpenTofu for new infrastructure roots; legacy Terraform roots migrate individually](decisions/ADR-003-opentofu-for-new-infrastructure.md) | infrastructure | New roots use OpenTofu with bpg/proxmox; existing Terraform roots keep Terraform until each is migrated with a verified no-change plan. |
| ADR-004 | accepted | [Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets](decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md) | secrets | Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill. |
| ADR-005 | accepted | [Windmill is the operations UI over a versioned service catalog](decisions/ADR-005-windmill-service-catalog.md) | orchestration | Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo. |
| ADR-006 | accepted | [Docker Compose first; k3s and Argo CD later, only where they add value](decisions/ADR-006-compose-first-kubernetes-later.md) | application | Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction. |
| ADR-007 | accepted | [Archive the legacy Codex workflow; keep live legacy IaC roots in place until migrated](decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md) | repository | Old AGENTS.md, roadmap, tasks and docs moved verbatim to docs/archive/codex-2026; legacy Terraform/Ansible code that still manages live resources stays at its path. |
| ADR-008 | accepted | [Bootstrap runs from the operator workstation; CT301 stays validation-only](decisions/ADR-008-workstation-bootstrap-ct301-validation-only.md) | execution | The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later. |
| ADR-009 | accepted | [The management VM is the operator's GNOME admin workstation](decisions/ADR-009-management-vm-gnome-admin-workstation.md) | pve-management | mgmt-control-01 is a GNOME admin workstation (Ubuntu 26.04, 8 vCPU host type, 10 GiB, 120 GiB) with RDP remote login, the IaC toolchain, Claude Code and Codex. |

## External references

_No external references captured yet. Create one with `harness new api-reference`._

## Documents by type

### Project overview

- **DOC-project-overview** [homelab-iac — project vision and overview](project-overview.md) (current) `overview, vision, rebuild, status` — Authoritative vision, rolling-rebuild strategy, principles, recovery philosophy, current status and confirmed decisions vs assumptions; read first.

### Architecture

- **ARCH-platform** [Target homelab platform architecture](architecture/platform.md) (current) — platform `architecture, platform, rebuild` — Layers, tool responsibilities, target stack, pve-management role, service catalog model, secrets and recovery boundaries for the rebuild.

### Investigation result

- **INV-legacy-inventory** [Legacy homelab inventory (archived repository, operator corrections, state review)](investigations/legacy-inventory.md) (needs-review) — inventory `investigation, inventory, legacy` — Legacy hosts, guests, services and local Terraform states, with retired hosts, stale state and endpoint hazards; starting point for the M000 live inventory.
- **INV-pve-management-bootstrap** [pve-management bootstrap — readiness and implementation plan](investigations/pve-management-bootstrap.md) (current) — pve-management `investigation, bootstrap, pve-management, plan` — Readiness, exact API privileges, SSH/TLS/state decisions, proposed VM values and the next step for provisioning mgmt-control-01 on pve-management; nothing applied.

## Implementation history

_No commit records. Generate with `harness history sync`._

## By tag

- **access**: TASK-007
- **age**: ADR-004, TASK-011
- **ansible**: TASK-009
- **architecture**: ARCH-platform
- **archive**: ADR-007
- **argocd**: ADR-006
- **automation**: M003
- **backup**: TASK-003, TASK-004, TASK-010
- **bootstrap**: ADR-002, ADR-008, INV-pve-management-bootstrap, M001
- **ci**: ADR-008
- **compose**: ADR-006
- **compute**: M004
- **cutover**: M007
- **decision**: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009
- **dependencies**: TASK-003
- **desktop**: ADR-009
- **flux**: ADR-006
- **future**: M008
- **gitops**: ADR-005, M008
- **harness**: TASK-001
- **infisical**: ADR-004
- **inventory**: INV-legacy-inventory, M000, TASK-002, TASK-003
- **investigation**: INV-legacy-inventory, INV-pve-management-bootstrap
- **k3s**: ADR-006
- **kubernetes**: ADR-006, M008
- **layout**: TASK-006
- **legacy**: ADR-007, INV-legacy-inventory
- **make**: TASK-006
- **management**: ADR-002, ADR-009
- **migration**: ADR-001, M005, TASK-005
- **observability**: M006
- **opentofu**: ADR-003, TASK-006, TASK-008
- **overview**: DOC-project-overview
- **pbs**: TASK-004
- **phase**: ADR-004, M002
- **plan**: INV-pve-management-bootstrap
- **planning**: M000, TASK-005
- **platform**: ARCH-platform
- **proxmox**: ADR-002, M004, TASK-002
- **pve-management**: ADR-009, INV-pve-management-bootstrap, M001, TASK-007, TASK-008
- **rebuild**: ARCH-platform, DOC-project-overview
- **recovery**: TASK-004, TASK-012
- **repository**: TASK-001
- **retirement**: M007
- **runbook**: TASK-012
- **runner**: ADR-008, TASK-009
- **secrets**: ADR-004, M002, TASK-011
- **security**: ADR-008
- **service-catalog**: ADR-005
- **sops**: ADR-004, TASK-011
- **state**: ADR-007, TASK-010
- **status**: DOC-project-overview
- **strategy**: ADR-001
- **terraform**: ADR-003
- **vision**: DOC-project-overview
- **windmill**: ADR-005, M003
- **workstation**: ADR-009

## By component

- **application**: ADR-006
- **execution**: ADR-008
- **infrastructure**: ADR-003
- **inventory**: INV-legacy-inventory
- **orchestration**: ADR-005
- **platform**: ADR-001, ARCH-platform
- **pve-management**: ADR-002, ADR-009, INV-pve-management-bootstrap
- **repository**: ADR-007
- **secrets**: ADR-004

## By technology

_No technology recorded._

## Broken references

_None._
