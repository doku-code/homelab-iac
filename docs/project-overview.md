---
id: DOC-project-overview
title: homelab-iac — project overview
summary: Vision, rolling-rebuild strategy, scope and navigation for the homelab rebuild; read first.
type: overview
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [overview, vision, rebuild]
related: [ARCH-platform, ADR-001, INV-legacy-inventory, M000]
---

# homelab-iac — project overview

## Purpose

`homelab-iac` is the central Infrastructure-as-Code repository of a personal homelab that is
being rebuilt into a reproducible, automated, self-hosted platform.

**Vision:** the homelab is reproducible from version-controlled definitions, with automated
provisioning, OS configuration, application deployment, secrets, networking (DNS/HTTPS),
monitoring, backup and recovery. Deploying a service becomes a mostly automated operation:
select it, supply its configuration (a Windmill form), validate inputs and dependencies,
provision, configure, fetch secrets, deploy, wire DNS/HTTPS, register monitoring and backups,
run health checks and record the result. Mature open-source tools are assembled for this;
no custom provisioning engine is built.

**Strategy:** a rolling rebuild ([ADR-001](decisions/ADR-001-rolling-infrastructure-rebuild.md)).
The running homelab provisions its replacement; services move one at a time with data
migration, validation and rollback; emptied machines are reinstalled and joined. The old
infrastructure builds the new until the new can manage itself. The first new node is
`pve-management`, a standalone bootstrap and recovery host ([ADR-002](decisions/ADR-002-pve-management-standalone-host.md)).

## Scope

In scope: Proxmox hosts and guests (OpenTofu), OS configuration (Ansible), Compose
applications, Forgejo Actions workflows, Windmill workflows, secret references (Phase,
SOPS + age bootstrap), DNS/proxy, monitoring and backup configuration, recovery runbooks.

Out of scope: secret values, Terraform/OpenTofu state, private tfvars, recovery keys — never
committed. The repository is public.

Principles: reproducibility, idempotency, one owner per layer, minimal complexity (no
Kubernetes/HA/distributed storage without need), security by design (scoped identities,
no secrets in Git or CI logs), independent recovery from a clean workstation, and small
incremental changes. Details in [ARCH-platform](architecture/platform.md).

## Structure

| Path | Content |
|------|---------|
| `docs/architecture/platform.md` | Target architecture: layers, owners, stack, service catalog, recovery |
| `docs/decisions/` | Decision records (ADR-001…) |
| `docs/investigations/` | Inventories and findings (legacy estate, live audits) |
| `milestones/`, `tasks/` | Roadmap M000–M008 and executable tasks |
| `docs/archive/codex-2026/` | Previous agent workflow, roadmap, tasks and runbooks — evidence only, not indexed |
| `terraform/stacks/`, `ansible/`, `services/`, `gitops/`, `scripts/`, `tests/`, `Makefile` | Legacy implementation still managing live resources ([ADR-007](decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)) |

New code follows the target layout in [ARCH-platform](architecture/platform.md#target-repository-layout).

## Where to look

- Current status and next task: `harness status`; roadmap: [dashboard](dashboard.md).
- Before infrastructure work: [ARCH-platform](architecture/platform.md) and the relevant ADR.
- What exists today (unverified): [INV-legacy-inventory](investigations/legacy-inventory.md).
- First milestones: [M000 inventory and migration planning](../milestones/M000-inventory-and-migration-planning.md),
  then [M001 bootstrap pve-management](../milestones/M001-bootstrap-pve-management.md).
