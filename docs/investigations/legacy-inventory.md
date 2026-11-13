---
id: INV-legacy-inventory
title: Legacy homelab inventory (archived repository, operator corrections, state review)
summary: Legacy hosts, guests, services and local Terraform states, with retired hosts, stale state and endpoint hazards; starting point for the M000 live inventory.
type: investigation
status: needs-review
importance: 4
created: 2026-11-12
updated: 2026-11-12
tags: [investigation, inventory, legacy]
component: inventory
topics: [proxmox, guests, services, state, migration]
related_tasks: [TASK-002, TASK-003]
related: [ARCH-platform, ADR-007, ADR-008, INV-pve-management-bootstrap]
---

# Legacy homelab inventory

## Question

What does the legacy repository say exists, which parts are managed by IaC, and which facts
must be re-verified before migration planning?

## Method

Read-only review of `ansible/inventories/homelab.yml`, `terraform/stacks/`, the local
(untracked) state file locations, and the archived documentation in
[docs/archive/codex-2026/](../archive/codex-2026/docs/README.md) at commit `915333c`
(2026-11-12). No live system was contacted. Everything below is **reported by legacy
documents** unless marked otherwise.

## Findings

### Proxmox hosts

| Host | Legacy role | Status to verify |
|------|-------------|------------------|
| `pve-core` | Essential services (Infisical-adjacent, PG candidate CT300, Windmill CT210, DNS/proxy guests) | Running services, capacity |
| `pve-lab` | Main compute, workstation VMs, K3s Stage A lab (VM303–305) | Headless since 2026-10-24; GPU workloads |
| `pve-k8s-01`, `pve-k8s-02` | Mini-PCs; legacy state records Tailscale routers CT306/CT307 on them | Exist (per state); role and membership to verify |
| `pve-management` | **New**, standalone bootstrap/recovery host at 192.168.0.10 (operator, 2026-11-12) | API identity, storage, network (TASK-007) |
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
| `pve-core-tfstate` | CT300 on `pve-core` | default `192.168.0.11` | Consistent with docs |
| `pve-core-garage` | CT209 on `pve-core` | default `192.168.0.11` | Consistent |
| `pve-core-windmill` | CT210 on `pve-core` | JSON tfvars without the key; default `192.168.0.11` | Consistent |
| `pve-tailscale-routers` | CT306/307 on `pve-k8s-01/02` | `192.168.0.11` | Consistent; nodes exist |

Protections added (repository only, nothing executed against infrastructure): Make refuses
plan/apply/import for any root whose private `proxmox_endpoint` (`terraform.tfvars` or `.json`) uses `192.168.0.10`/`.12`
(`LEGACY_ENDPOINT_GUARD`), and refuses live operations on the two `pve-compute` roots (`RETIRED_ROOT`).
The retired hosts were removed from `ansible/inventories/homelab.yml` (the `proxmox` group is targeted
by `audit-linux.yml` and `deploy-node-exporter.yml`) and from the Prometheus node targets.
The workstation's `known_hosts` still holds `pve-infra`'s keys for 192.168.0.10, so SSH fails closed.

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
