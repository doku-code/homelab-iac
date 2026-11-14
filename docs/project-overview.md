---
id: DOC-project-overview
title: homelab-iac — project vision and overview
summary: Authoritative vision, rolling-rebuild strategy, principles, recovery philosophy, current status and confirmed decisions vs assumptions; read first.
type: overview
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [overview, vision, rebuild, status]
aliases: [PROJECT_VISION]
related: [ARCH-platform, ADR-001, ADR-008, INV-legacy-inventory, INV-pve-management-bootstrap, M000, M001]
---

# homelab-iac — project vision and overview

This is the authoritative project vision (the briefing of 2026-11-12). Architecture details live
in [ARCH-platform](architecture/platform.md); decisions in [docs/decisions/](decisions/); work in
[milestones](../milestones/) and [tasks](../tasks/). Other documents link here instead of repeating it.

## Purpose

`homelab-iac` is the central Infrastructure-as-Code repository of a personal homelab that is
being transformed from a manually maintained estate into a reproducible, automated platform.

**Vision:** the homelab is reproducible from version-controlled definitions, with automated
provisioning, OS configuration, application deployment, secrets, networking, monitoring, backup
and recovery, and no reliance on undocumented knowledge. Deploying a service becomes a mostly
automated operation:

1. select the service or component; 2. supply its configuration (eventually a Windmill form);
3. validate configuration and dependencies; 4. provision infrastructure; 5. configure the OS;
6. retrieve secrets; 7. deploy the application; 8. configure networking, DNS and HTTPS;
9. register monitoring and backups; 10. run health checks; 11. record the resulting state.

This is assembled progressively from mature open-source tools; no custom provisioning engine.

**Strategy — rolling rebuild** ([ADR-001](decisions/ADR-001-rolling-infrastructure-rebuild.md)):
the existing homelab builds the new one, the new one gradually replaces the old one, and freed
hardware joins the new environment. Per service: deploy a clean replacement, migrate data and
configuration, validate, prepare rollback, cut over, retire the old instance. An emptied machine
is reinstalled and joined. No step may require every machine at once or a full hardware duplicate;
minimal downtime, no data loss and a rollback path are mandatory.

## Scope

In scope: Proxmox hosts and guests (OpenTofu), OS configuration (Ansible), Compose applications,
Forgejo Actions and Windmill workflows, secret references, DNS/proxy, monitoring and backup
configuration, bootstrap and recovery runbooks.

Never in Git: secret values, OpenTofu/Terraform state, private tfvars, recovery keys. The repository is public.

### Principles

| Principle | Meaning here |
|-----------|--------------|
| Reproducibility | Rebuildable from Git + bootstrap credentials + state + off-host data backups; no unreproducible manual change |
| Idempotency | Re-running automation converges without duplicates or breakage |
| Separation of concerns | Hypervisor, provisioning, OS config, app config and orchestration stay separate layers ([ARCH-platform](architecture/platform.md#layers-and-owners)) |
| Minimal complexity | Compose by default; no Kubernetes, HA or distributed storage without demonstrated need |
| Security by design | Dedicated scoped identities, no plaintext secrets/state/keys in Git, protected CI logs, verified TLS |
| Independent recovery | A clean workstation with the repo, recovery keys and off-host backups can start recovery |
| Incremental delivery | Smallest useful change, tested, then the next; no oversized milestones |

### Bootstrap and disaster-recovery philosophy

- `pve-management` is a standalone bootstrap, orchestration and recovery host, not a compute node
  ([ADR-002](decisions/ADR-002-pve-management-standalone-host.md)). It is first provisioned *from*
  the existing infrastructure; the management VM is never a prerequisite of its own creation.
- Every bootstrap step also runs from an administrator workstation. Forgejo, Phase and Windmill
  are conveniences during normal operation, never requirements for recovering themselves.
- Bootstrap secrets are SOPS + age encrypted; age private keys and recovery material are held
  outside the infrastructure they protect ([ADR-004](decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)).
- Backups count only once a restore has been tested. Pod rescheduling, snapshots or CI success
  are not data recovery.

## Structure

| Path | Content |
|------|---------|
| `docs/architecture/platform.md` | Current vs target architecture, layer owners, stack, service catalog, recovery flow |
| `docs/decisions/` | Decision records ADR-001…009 |
| `docs/investigations/` | Legacy inventory, pve-management bootstrap readiness and plan |
| `milestones/`, `tasks/` | Roadmap M000–M008 and the tasks of the next two milestones |
| `docs/archive/codex-2026/` | Previous agent workflow, roadmap, tasks and runbooks — evidence only, not indexed |
| `terraform/`, `ansible/`, `services/`, `gitops/`, `scripts/`, `tests/`, `Makefile` | Legacy implementation still managing live resources ([ADR-007](decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)) |

### Roadmap

M000 inventory and migration planning (active) → **M001 bootstrap `pve-management`** (first
implementation milestone) → M002 Phase → M003 Windmill → M004 new compute → M005 rolling
application migration → M006 observability → M007 core cutover and retirement → M008 future
(k3s + Argo CD, self-service catalog). Progress: [dashboard](dashboard.md).

### Current status (2026-11-12)

- Repository reset onto the agent harness; legacy documentation archived; this direction documented.
- `pve-infra` and `pve-compute` are permanently retired; `192.168.0.10` is `pve-management` (fresh
  Proxmox VE, standalone, no guests). Ports 8006/22 answer; its API identity, storage and network are
  not verified yet.
- M001 is prepared offline: OpenTofu root `terraform/stacks/pve-management-control` (reusing
  `headless-vm`), Ansible playbook, guarded `mgmt-*` Make targets, mocked tests. Nothing applied.
- Legacy services keep running; nothing has been migrated. Nine legacy Terraform roots hold their only
  state locally; four still point at `192.168.0.10` and two record retired `pve-compute` guests —
  Make now refuses those operations ([INV-legacy-inventory](investigations/legacy-inventory.md)).
- Next: operator creates the dedicated API token, then `make mgmt-discover`
  ([INV-pve-management-bootstrap](investigations/pve-management-bootstrap.md)).

### Confirmed decisions vs assumptions

| Item | Status |
|------|--------|
| Rolling rebuild; old infrastructure builds the new | **Confirmed** (ADR-001) |
| `pve-management` standalone, minimal hypervisor, Ubuntu management VM | **Confirmed** (ADR-002) |
| OpenTofu for new roots, `bpg/proxmox` provider; legacy roots migrate one by one | **Confirmed** (ADR-003) |
| Windmill as operations UI over versioned workflows and a service catalog | **Confirmed** (ADR-005) |
| Compose first; k3s + Argo CD later; Flux not the target | **Confirmed** (ADR-006) |
| SOPS + age for bootstrap secrets | **Confirmed** (ADR-004) |
| Phase as the runtime secret store | **Confirmed direction**; deployment gated on validating the self-hosted free edition (ADR-004) |
| Bootstrap from the workstation; CT301 validation-only, never Proxmox credentials | **Confirmed** (ADR-008) |
| `pve-infra`, `pve-compute` permanently retired; `192.168.0.10` is `pve-management` | **Confirmed** (operator) |
| Former `pve-infra`/`pve-compute` workloads safely migrated | **Unknown**: not proven by retirement (TASK-002/003) |
| Legacy host/service inventory | **Assumption** from archived docs and state review ([INV-legacy-inventory](investigations/legacy-inventory.md)) |
| Management VM `mgmt-control-01`: GNOME admin workstation, VMID 100, `192.168.0.39`, 8 vCPU / 10 GiB / 120 GiB, Ubuntu 26.04 | **Confirmed** (ADR-009, discovery 2026-11-14) |
| Spare machine for the new compute environment; cluster topology | **Unknown** (M004) |
| State backend for new roots | **Open** (TASK-010); Garage rejected, PostgreSQL candidate never production-qualified |

## Where to look

- Current status and next task: `harness status`; roadmap: [dashboard](dashboard.md).
- Before infrastructure work: [ARCH-platform](architecture/platform.md) and the relevant ADR.
- First implementation: [INV-pve-management-bootstrap](investigations/pve-management-bootstrap.md) and
  [M001](../milestones/M001-bootstrap-pve-management.md).
- What exists today (unverified): [INV-legacy-inventory](investigations/legacy-inventory.md).
