---
title: homelab-iac — project vision and overview
description: Authoritative vision, rolling-rebuild strategy, target stack and roadmap M000-M012, current status, confirmed decisions vs pending technical choices; read first.
published: true
tags:
- overview
- current
- vision
- rebuild
- status
editor: markdown
date: '2026-11-18T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# homelab-iac — project vision and overview

> **ID:** DOC-project-overview · **Type:** overview · **Status:** current · **Updated:** 2026-11-18 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/project-overview.md)

This is the authoritative project vision (briefings of 2026-11-12 and 2026-11-14). Architecture details live
in [ARCH-platform](/docs/architecture/platform); decisions in [docs/decisions/](/docs/decisions); work in
[milestones](/milestones) and [tasks](/tasks). Other documents link here instead of repeating it.

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

**Strategy — rolling rebuild** ([ADR-001](/docs/decisions/adr-001-rolling-infrastructure-rebuild)):
the existing homelab builds the new one, the new one gradually replaces the old one, and freed
hardware joins the new environment. Per service: deploy a clean replacement, migrate data and
configuration, validate, prepare rollback, cut over, retire the old instance. An emptied machine
is reinstalled and joined. No step may require every machine at once or a full hardware duplicate;
minimal downtime, no data loss and a rollback path are mandatory.

## Scope

In scope: Proxmox hosts and guests (OpenTofu), OS configuration (Ansible), k3s and its applications
(Argo CD), Forgejo Actions and Windmill workflows, secret references, DNS/proxy, monitoring and backup
configuration, bootstrap and recovery runbooks.

Never in Git: secret values, OpenTofu/Terraform state, private tfvars, recovery keys. The repository is public.

### Principles

| Principle | Meaning here |
|-----------|--------------|
| Reproducibility | Rebuildable from Git + bootstrap credentials + state + off-host data backups; no unreproducible manual change |
| Idempotency | Re-running automation converges without duplicates or breakage |
| Separation of concerns | Hypervisor, provisioning, OS config, app config and orchestration stay separate layers ([ARCH-platform](/docs/architecture/platform#layers-and-owners)) |
| Minimal complexity | k3s for applications from the start; no HA claims, Ceph or extra services before the hardware and a real need exist |
| Security by design | Dedicated scoped identities, no plaintext secrets/state/keys in Git, protected CI logs, verified TLS |
| Independent recovery | A clean workstation with the repo, recovery keys and off-host backups can start recovery |
| Incremental delivery | Smallest useful change, tested, then the next; no oversized milestones |

### Target stack and responsibilities

**Proxmox → k3s → Headlamp → external NVMe-backed storage / CSI → PostgreSQL + Patroni → Phase →
Argo CD + Windmill → applications.** Layers and owners: [ARCH-platform](/docs/architecture/platform).

- The new Proxmox cluster is founded on `pve-management`; `pve-core` joins first, reclaimed hosts follow
  ([ADR-010](/docs/decisions/adr-010-new-proxmox-cluster-on-pve-management)).
- k3s runs applications from the start; Headlamp administers it, Argo CD reconciles it from Forgejo,
  Windmill automates workflows, a dedicated Forgejo runner executes approved jobs
  ([ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp), [ADR-014](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner)).
- Persistent data lives on NVMe-backed storage **outside** k3s, consumed through CSI; Ceph later;
  **TrueNAS is the backup destination, never live PVC storage**
  ([ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups)).
- A central PostgreSQL with Patroni serves the applications, one database and role each
  ([ADR-013](/docs/decisions/adr-013-central-postgresql-patroni)); Phase replaces Infisical incrementally
  ([ADR-004](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap)).
- Every bootstrap step stays runnable from the operator workstation; Forgejo, Phase and Windmill are
  never required to recover themselves (ADR-008).

## Structure

| Path | Content |
|------|---------|
| `docs/architecture/platform.md` | Current vs target architecture, layer owners, stack, service catalog, recovery flow |
| `docs/decisions/` | Decision records ADR-001…014 (ADR-002, ADR-006 superseded) |
| `docs/investigations/` | Legacy inventory, pve-management bootstrap readiness and plan |
| `milestones/`, `tasks/` | Roadmap M000–M012 and the tasks of the upcoming work |
| `docs/archive/codex-2026/` | Previous agent workflow, roadmap, tasks and runbooks — evidence only, not indexed |
| `terraform/`, `ansible/`, `services/`, `gitops/`, `scripts/`, `tests/`, `Makefile` | Legacy implementation still managing live resources ([ADR-007](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots)) |

### Roadmap

M001 management workstation (closing) → M002 new Proxmox cluster (**completed**) → **M003 dedicated
deployment runner** → M004 k3s bootstrap → M005 Headlamp → M006 external NVMe-backed storage → M007
PostgreSQL platform → M008 Phase → M009 Argo CD and Windmill → M010 rolling application migration → M011
Ceph and expansion → M012 backups and finalization. M000 (inventory), M013 (NetBox inventory and
IPAM) and M014 (single sign-on with Authentik), both added 2026-11-18, run alongside.
Progress: [dashboard](/docs/dashboard).

### Current status (2026-11-16)

- New cluster `doku-lab`, quorate with four nodes: `pve-management` (.10), `pve-core` (.11), `pve-infra`
  (.12, fresh install) and the new `pve-lab` (.16); only VM 100 exists
  ([inventory](/docs/investigations/new-proxmox-cluster-inventory)).
- `mgmt-control-01` (VM 100, 192.168.0.39) is a genuine Ubuntu Desktop, configured by Ansible, and holds the
  OpenTofu state: the operator works from it ([handoff](/docs/handoff)).
- The **old environment** is the old `pve-lab` at **192.168.0.14** (Ryzen 9 9950X3D), outside the new cluster,
  running the legacy services (TrueNAS keeps Forgejo). Emptied at the end of M010, it becomes `pve-compute`.
- Legacy Terraform roots keep their local state (on the Mac) and are refused on every new-cluster address
  ([INV-legacy-inventory](/docs/investigations/legacy-inventory)).

### Current priority (operator, 2026-11-14)

Build first, harden later: local OpenTofu state, existing secret mechanisms (Infisical) and existing
backup systems (TrueNAS, PBS) are enough for now. Remote state, automated backups, disaster recovery
design and advanced secret management are reviewed once the new infrastructure has taken shape; they are
not prerequisites for deploying services. Migration safety (no data loss, the original keeps running
until its replacement works) still applies.

### Confirmed decisions vs pending choices

Confirmed (operator): rolling rebuild with the existing infrastructure (ADR-001); Proxmox as hypervisor;
new cluster `doku-lab` on `pve-management`, `pve-core`, `pve-infra` and the new `pve-lab` (.16), the old
`pve-lab` (.14) as continuity host until it becomes `pve-compute` (ADR-010); OpenTofu for new roots (ADR-003); k3s as application
platform, Headlamp as Kubernetes UI, Argo CD for GitOps, Windmill for operational automation (ADR-011,
ADR-005); Forgejo as source of truth with a dedicated deployment runner (ADR-014); persistent data
outside the k3s cluster on the physical hosts' NVMe, TrueNAS as backup destination, Ceph as future
distributed storage (ADR-012); PostgreSQL with Patroni on three VMs outside k3s (ADR-013, ADR-015); Phase replacing Infisical (ADR-004);
the management workstation (ADR-009); local OpenTofu state for now; incremental progress over premature
complexity.

| Pending technical choice | Decided in |
|--------------------------|------------|
| Initial external storage implementation, protocol and CSI driver; need for a storage VM | M006 |
| First k3s VM sizing and placement (proposal in the inventory); ingress | M004 |
| Ceph timing, networking, quorum and OSD topology | M011 |
| ~~PostgreSQL operator version, Patroni replication mode~~ decided: three Patroni VMs outside k3s, quorum-synchronous (ADR-015) | M007 done |
| Phase self-hosted compatibility (licence, chart, external PostgreSQL, Authentik) | M008 |
| Backup implementation details | M012 |
| Remaining application migration order | M010 |
| Former `pve-infra`/`pve-compute` workloads all accounted for | M000 (TASK-002) |

## Where to look

- Current work and next task: [handoff](/docs/handoff), `harness status`; roadmap: [dashboard](/docs/dashboard).
- Before infrastructure work: [ARCH-platform](/docs/architecture/platform) and the relevant ADR.
- Bootstrap pattern reused for new hosts: [INV-pve-management-bootstrap](/docs/investigations/pve-management-bootstrap).
- What exists today (unverified): [INV-legacy-inventory](/docs/investigations/legacy-inventory).
