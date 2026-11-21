---
title: Legacy homelab inventory
description: Legacy hosts, guests, services and local Terraform states, with retired hosts, stale state and endpoint hazards; starting point for the M000 live inventory.
published: true
tags:
- investigation
- needs-review
- inventory
- legacy
editor: markdown
date: '2026-11-21T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# Legacy homelab inventory

> **ID:** INV-legacy-inventory · **Type:** investigation · **Status:** needs-review · **Updated:** 2026-11-21 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/investigations/legacy-inventory.md)

## Question

What does the legacy repository say exists, which parts are managed by IaC, and which facts
must be re-verified before migration planning?

## Method

Read-only review of `ansible/inventories/homelab.yml`, `terraform/stacks/`, the local
(untracked) state file locations, and the archived documentation in
[docs/archive/codex-2026/](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/archive/codex-2026/docs/README.md) at commit `915333c`
(2026-11-12). No live system was contacted. Everything below is **reported by legacy
documents** unless marked otherwise.

## Findings

### Proxmox hosts

| Host | Legacy role | Status to verify |
|------|-------------|------------------|
| `pve-core` | **Emptied** (operator, 2026-11-14): its workloads moved to `pve-lab`; Ryzen 7 6800H, 8C/16T, 32 GB DDR5; to be reinstalled and joined to the new cluster (TASK-013) | NVMe layout |
| `pve-lab` | Main compute, workstation VMs, K3s Stage A lab (VM303–305), and since 2026-11-14 the former `pve-core` workloads; continuity host, do not disrupt | Headless since 2026-10-24; GPU workloads |
| `pve-k8s-01`, `pve-k8s-02` | Mini-PCs; legacy state records Tailscale routers CT306/CT307 on them | Exist (per state); role and membership to verify |
| `pve-management` | **New** host at 192.168.0.10 (operator, 2026-11-12); founding node of the new cluster (ADR-010) | API identity, storage, network (TASK-007) |
| ~~`pve-infra`~~ | **Permanently retired** (operator, 2026-11-12); its former address now belongs to `pve-management` | Former workloads' migration not proven |
| ~~`pve-compute`~~ | **Permanently retired** (operator, 2026-11-12) | Former workloads' migration not proven |

### Guests and services (legacy IDs)

| Service | Legacy placement | IaC-managed? |
|---------|------------------|--------------|
| Forgejo (+ OCI registry) | TrueNAS app | No |
| Forgejo runner (`forgejo-homelab-iac-runner`, serves CI) | CT301, **current host unknown** (state says retired `pve-compute`) | Terraform state stale; Ansible role |
| Infisical | VM207 | No (manual) |
| Monitoring (Prometheus/Grafana Compose) | VM208 `deb13-monitoring` | Terraform + Ansible + Compose |
| AdGuard Home | CT200 | No |
| Homepage | CT201 | No (fresh K3s copy existed in Stage A) |
| Wiki.js | CT202 | No |
| Print server (CUPS) | CT203 | No |
| Vaultwarden | CT206 | No |
| Garage (rejected state backend) | CT209 | Terraform + Ansible (`pve-core-garage`) |
| Windmill CE | CT210 on `pve-core`, app not verified | Terraform + Ansible + Compose (`pve-core-windmill`) |
| PostgreSQL state-backend candidate | CT300 `tfstate` | Terraform + Ansible (`pve-core-tfstate`), holds no production state |
| Tailscale subnet routers | CT306/307 | Terraform + Ansible, convergence incomplete |
| K3s Stage A + Flux demo + Homepage | VM303–305 on `pve-lab` | Terraform + Ansible + `gitops/stage-a` |
| Workstations | VM502, VM601 (and others) on `pve-lab` | Terraform + Ansible (`pve-lab-workstations`) |
| Caddy, Nextcloud, Plex, TrueNAS, PBS, pfSense | Various / physical | No; placement unknown |

### Local Terraform state (verified on the operator workstation, 2026-11-12)

Untracked `terraform.tfstate` files exist beside the code in nine roots. Only node and ID were read
(no attributes). They are the only record of ownership and are not backed up by Git.

| Root | State records | API endpoint in private tfvars | Assessment |
|------|---------------|-------------------------------|------------|
| `deb13-monitoring` | VM208 + image on `pve-core` | `192.168.0.10` | **Endpoint now reaches `pve-management`** |
| `pve-lab-workstations` | VM501–503, 601, 602 on `pve-lab` | `192.168.0.10` | **Endpoint now reaches `pve-management`** |
| `pve-lab-k3s` | VM303–305 + image on `pve-lab` | `192.168.0.10` | **Endpoint now reaches `pve-management`** |
| `pve-lab-controller` | none | `192.168.0.10` | **Endpoint now reaches `pve-management`** |
| `pve-compute-forgejo-runner-migration` | CT301 on `pve-compute` | `192.168.0.12` | **Stale**: CT301 still runs CI, so it lives elsewhere now |
| `pve-compute-forgejo-runner` | CT300 on `pve-compute` | `192.168.0.12` | **Stale**: retired runner never removed from state; ID 300 is now `tfstate` on `pve-core` |
| `pve-core-tfstate` | CT300 on `pve-core` | default `192.168.0.11` | **Stale**: guest moved to `pve-lab` (operator, 2026-11-14); guard the address before `pve-core` is reinstalled |
| `pve-core-garage` | CT209 on `pve-core` | default `192.168.0.11` | **Stale**: guest moved to `pve-lab` (operator, 2026-11-14); guard the address before `pve-core` is reinstalled |
| `pve-core-windmill` | CT210 on `pve-core` | JSON tfvars without the key; default `192.168.0.11` | **Stale**: guest moved to `pve-lab` (operator, 2026-11-14); guard the address before `pve-core` is reinstalled |
| `pve-tailscale-routers` | CT306/307 on `pve-k8s-01/02` | `192.168.0.11` | Consistent; nodes exist |

Protections added (repository only, nothing executed against infrastructure): Make refuses
plan/apply/import for any root whose private `proxmox_endpoint` (`terraform.tfvars` or `.json`) uses `192.168.0.10`/`.12`
(`LEGACY_ENDPOINT_GUARD`), and refuses live operations on the two `pve-compute` roots (`RETIRED_ROOT`).
The retired hosts were removed from `ansible/inventories/homelab.yml` (the `proxmox` group is targeted
by `audit-linux.yml` and `deploy-node-exporter.yml`) and from the Prometheus node targets.
The workstation's `known_hosts` still holds `pve-infra`'s keys for 192.168.0.10, so SSH fails closed.

### New cluster reuses names and addresses (2026-11-16)

The new cluster ([INV-new-proxmox-cluster-inventory](/docs/investigations/new-proxmox-cluster-inventory)) reuses
`192.168.0.10/.11/.12/.16` and the names `pve-core`, `pve-infra` and `pve-lab`. The **old environment is
reachable only at 192.168.0.14** (old `pve-lab`, Ryzen 9 9950X3D), which keeps running the legacy
services; `pve-compute` is the future name of that machine after its final reinstall. Make now refuses
every legacy root whose endpoint is a new-cluster address (`LEGACY_ENDPOINT_GUARD`), and `pve-core` left
the legacy `proxmox` Ansible group. Legacy roots stay on Terraform with their local state on the Mac
(not migrated; an inactive archive is on `mgmt-control-01` in `.local/legacy-state-archive-2026-11-16.tar`);
repoint a root at `.14` only when that root is worked on (M010).

### Retired hosts (resolved 2026-11-12)

The operator confirmed that `pve-infra` and `pve-compute` are permanently retired and that
`192.168.0.10` belongs to `pve-management`. Retirement does not prove that their former workloads
or data were migrated: the services the legacy docs placed there (DNS/proxy, the runner) must be
located in TASK-002/TASK-003. Historical documents in the archive keep their original wording.

## Inferences

- Most user-facing services (Forgejo, Infisical, AdGuard, Vaultwarden, Wiki.js, Caddy) were
  configured manually; IaC covers mainly guest lifecycle for infrastructure helpers.
- The legacy roots are safe to keep as-is; their value is ownership of live guests, not their design.

## Open questions

- Current host list, cluster membership and free capacity (TASK-002).
- Correct API endpoint for the four roots still using `192.168.0.10` (likely the legacy cluster API on `pve-core`; operator decision).
- Where CT301 runs now, and how to reconcile the two stale `pve-compute` states (re-import, `state rm` or archive) — operator decision, no automatic reconciliation.
- Where Caddy, AdGuard and the Tailscale routers run today; DNS/route dependencies (TASK-003).
- Backup coverage per service and whether a PBS restore actually works (TASK-003, TASK-004).
- Which machine is the "remaining spare machine" for the new compute environment (M004).

## Update 2026-11-21: replaced guests deleted

On the operator's word, the guests of the old host whose replacements run on doku-lab were deleted there
(`pct destroy` / `qm destroy` with `--purge`, each only after checking that it was stopped and still carried
the expected name): CT200 AdGuard, CT201 Homepage, CT202 Wiki.js, CT210 Windmill, VM 207 Infisical, VM 208
monitoring, VM 303 to 305 (Stage A k3s). Nothing else on the old host was changed. The Terraform roots
`deb13-monitoring`, `pve-lab-k3s` and `pve-core-windmill` now describe guests that no longer exist; their
states (on the Mac, archive in `.local/`) are history, not something to apply. The current list of what
is left is the [inventory page](/docs/reference/infrastructure-inventory), generated from NetBox.
