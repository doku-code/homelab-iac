---
id: ARCH-platform
title: Target homelab platform architecture
summary: Layers, tool responsibilities, target stack, pve-management role, service catalog model, secrets and recovery boundaries for the rebuild.
type: architecture
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [architecture, platform, rebuild]
component: platform
topics: [opentofu, ansible, compose, windmill, phase, sops, forgejo, proxmox, recovery]
related: [DOC-project-overview, INV-legacy-inventory]
related_decisions: [ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007]
related_implementations: []
---

# Target homelab platform architecture

## Overview

The homelab is rebuilt as a reproducible platform: every resource, host configuration and
service deployment is declared in this repository, secrets live outside Git, and recovery
starts from a clean workstation. The rebuild is **rolling** ([ADR-001](../decisions/ADR-001-rolling-infrastructure-rebuild.md)):
the existing infrastructure provisions its replacement, services move one at a time, and
reclaimed hardware joins the new environment.

This document is the target. What is actually deployed is recorded in tasks and milestone
evidence; the legacy estate is described in [INV-legacy-inventory](../investigations/legacy-inventory.md).

## Structure

### Current versus target

| Concern | Current (legacy, partly verified) | Target |
|---------|-----------------------------------|--------|
| Provisioning | Terraform ≥ 1.16 + `bpg/proxmox` 0.112.0, per-guest roots, local state on one workstation | OpenTofu roots with backed-up remote state (TASK-010) |
| Proxmox auth | Mixed: API token (Stage A) and `root@pam` password from Infisical (Tailscale, Windmill flows) | Dedicated scoped API token per environment |
| Execution | Operator-run Make targets; CI is validation-only on the CT301 runner (open trust gate) | Same Make entrypoints, plus a trusted runner on the management VM and Windmill triggers |
| Services | Mostly hand-configured guests (Forgejo on TrueNAS, Infisical, AdGuard, Caddy, Vaultwarden, Wiki.js…) | `services/<service>/` catalog entries deployed by Ansible + Compose |
| Secrets | Infisical (Universal Auth) | Phase at runtime, SOPS + age for bootstrap |
| Kubernetes | K3s Stage A lab + Flux demo on `pve-lab` | None by default; k3s + Argo CD later (ADR-006) |
| Management | No dedicated management host | `pve-management` with management VM(s) |

### Layers and owners

Each layer has exactly one owner. A tool never writes objects another layer owns.

| Layer | Owner | Owns | Never does |
|-------|-------|------|------------|
| Hypervisor | Proxmox VE (minimal hosts) | Compute, local storage, networking bridges | Run application stacks on the host |
| Infrastructure | OpenTofu, `bpg/proxmox` provider ([ADR-003](../decisions/ADR-003-opentofu-for-new-infrastructure.md)) | VMs/LXCs, disks, NICs, cloud-init, API-level resources | Install packages, configure apps |
| OS configuration | Ansible | Users, SSH, packages, hardening, Docker engine, agents, runner | Create VMs, hold app topology |
| Application | Docker Compose (k3s + Argo CD later, [ADR-006](../decisions/ADR-006-compose-first-kubernetes-later.md)) | Container topology, volumes, app config files | Provision hosts |
| Source of truth | Forgejo | Code, deployment definitions, workflow history | Store secrets in repositories |
| Execution | Forgejo Actions runners | Run reviewed, versioned workflows | Accept untrusted code with privileged credentials |
| Orchestration UI | Windmill ([ADR-005](../decisions/ADR-005-windmill-service-catalog.md)) | Forms, schedules, run history; calls versioned workflows | Become an infrastructure engine or a recovery dependency |
| Runtime secrets | Phase, target ([ADR-004](../decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)) | Service/CI secrets, machine identities | Be required to recover itself |
| Bootstrap secrets | SOPS + age | Credentials needed before Phase/Forgejo exist | Hold day-to-day app secrets |
| Edge | Caddy, AdGuard Home, pfSense | HTTPS, internal DNS (`home.arpa`), routing/firewall | — |
| Identity | Authentik | SSO for humans and supported apps | Gate break-glass recovery |
| Data protection | PBS + TrueNAS | Guest backups, persistent datasets | — |
| Observability | Prometheus, Loki, Grafana | Metrics, logs, dashboards, alerts | Sit in the bootstrap critical path |

Infisical stays the runtime secret store until Phase is deployed, backed up, tested and its
consumers are migrated.

### Hosts

| Host | Role in the target | Notes |
|------|--------------------|-------|
| `pve-management` | Standalone bootstrap, orchestration and recovery host ([ADR-002](../decisions/ADR-002-pve-management-standalone-host.md)) | Fresh Proxmox VE, not joined to the compute cluster. Runs only management VMs. |
| Compute cluster | Application workloads | Topology, quorum and storage planned in M004; two nodes never imply HA. |
| Legacy hosts (`pve-core`, `pve-lab`, others) | Keep running services until migrated, then reinstalled and joined | Inventory in M000. |

On `pve-management` the first guest is an **Ubuntu Server management VM** with the IaC
toolchain (OpenTofu, Ansible, SOPS/age, Phase CLI) and a dedicated Forgejo runner. Further
management applications (Windmill, Phase) run in their own VMs when resources allow.

### Target repository layout

New code follows this layout; legacy directories stay where they are until their resources
are migrated or retired ([ADR-007](../decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)).

```
modules/opentofu/<module>/     reusable OpenTofu modules (proxmox-guest, ...)
stacks/<environment>/<stack>/  one OpenTofu root = one state = one owner
ansible/roles/<role>/          reusable roles; playbooks stay thin
services/<service>/            one self-contained deployable unit per service:
  service.yaml                 catalog entry: inputs schema, dependencies, placement, secrets refs, health check
  compose.yaml                 application topology (when Compose-based)
  config/                      versioned application configuration templates
windmill/                      Windmill scripts/flows synced from Git (thin callers)
.forgejo/workflows/            validation and approved deployment workflows
secrets/bootstrap/*.sops.yaml  SOPS-encrypted bootstrap material only (age recipients in .sops.yaml)
```

Legacy layout still in use: `terraform/stacks/*` (local state beside the code),
`ansible/playbooks/*`, `services/monitoring`, `services/windmill`, `gitops/stage-a`.

## Key flows

### Deploy a service (target)

1. Operator picks a service in Windmill; the form is generated from `services/<service>/service.yaml`.
2. Windmill validates the inputs against that schema and triggers the versioned Forgejo
   deployment workflow (or the same Make/script entrypoint), passing only non-secret inputs.
3. The workflow runs `tofu plan` for the guest, then requires approval before `apply`.
4. Ansible configures the OS and deploys the Compose project; secrets are fetched from
   Phase at runtime by a scoped machine identity.
5. DNS, Caddy route, monitoring and backup registration are applied from the same catalog entry.
6. Health checks run; the result (commit, plan summary, outputs) is reported back to Windmill.

Every step is runnable without Windmill from a workstation (`make`/scripts), so Windmill is
a convenience layer, not a dependency.

### Migrate an existing service (per service, M005)

Analyse dependencies and config → implement the reproducible deployment → provision the
replacement → migrate persistent data → validate function, monitoring and backups → controlled
cutover with a rollback path → verify → retire the old workload once safe. An emptied
physical host is reinstalled and joined to the new environment.

### Recover

A clean workstation with the repository (or its external mirror), the age private key held
outside the homelab, and off-host backups can: provision `pve-management` guests with
OpenTofu, configure them with Ansible using SOPS-decrypted bootstrap credentials, restore
Forgejo/Phase/Windmill data from backups, then resume normal workflows.

## Constraints

- No `tofu apply`/`destroy`, VM deletion, storage, network, firewall or credential changes
  without explicit operator approval for that operation.
- One writable state per OpenTofu root; state is never committed. Remote state and its
  backups are designed in TASK-010 before new roots hold real resources.
- Recovery never depends on the service being recovered (Forgejo, Phase, Windmill).
- Validation CI receives no infrastructure credentials; privileged workflows run only from
  trusted triggers on protected refs.
- Do not add Kubernetes, distributed storage, HA clusters or new services without a
  demonstrated need.
- Avoid SaaS dependencies and enterprise-only licensing; verify licences before adoption.
