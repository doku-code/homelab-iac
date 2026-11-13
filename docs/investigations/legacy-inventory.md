---
id: INV-legacy-inventory
title: Legacy homelab inventory (from the archived repository, unverified)
summary: Hosts, guests, services and local Terraform states as described by the legacy repo at 915333c; starting point for the M000 live inventory, not current truth.
type: investigation
status: needs-review
importance: 4
created: 2026-11-12
updated: 2026-11-12
tags: [investigation, inventory, legacy]
component: inventory
topics: [proxmox, guests, services, state, migration]
related_tasks: [TASK-002, TASK-003]
related: [ARCH-platform, ADR-007]
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
| `pve-compute` | Forgejo runner CT301 | Membership, guests |
| `pve-infra` | DNS/proxy, Tailscale routers; was being evacuated | **See discrepancy below** |
| `pve-k8s-01`, `pve-k8s-02` | Planned mini-PC compute nodes (not deployed) | Do they exist / are they the "spare machine"? |

### Guests and services (legacy IDs)

| Service | Legacy placement | IaC-managed? |
|---------|------------------|--------------|
| Forgejo (+ OCI registry) | TrueNAS app | No |
| Forgejo runner | CT301 on `pve-compute` | Terraform + Ansible (`pve-compute-forgejo-runner*`) |
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

Untracked `terraform.tfstate` files exist beside the code in nine roots:
`deb13-monitoring`, `pve-compute-forgejo-runner`, `pve-compute-forgejo-runner-migration`,
`pve-core-garage`, `pve-core-tfstate`, `pve-core-windmill`, `pve-lab-k3s`,
`pve-lab-workstations`, `pve-tailscale-routers`. Only `pve-lab-controller` has none.
These are the only record of those resources' ownership and are not backed up by Git.

### Discrepancy: pve-infra vs pve-management

The legacy inventory maps `pve-infra` to the management address now used by the freshly
installed `pve-management`. Either `pve-infra` was reinstalled as `pve-management` or the
inventory is stale. Any legacy playbook targeting `pve-infra` now reaches a different host;
strict host-key checking should fail closed, but this must be confirmed and the inventory
corrected in TASK-002. Services the legacy docs placed on `pve-infra` (DNS/proxy, Tailscale
routers) must be located.

## Inferences

- Most user-facing services (Forgejo, Infisical, AdGuard, Vaultwarden, Wiki.js, Caddy) were
  configured manually; IaC covers mainly guest lifecycle for infrastructure helpers.
- The legacy roots are safe to keep as-is; their value is ownership of live guests, not their design.

## Open questions

- Current host list, cluster membership and free capacity (TASK-002).
- Where Caddy, AdGuard and the Tailscale routers run today; DNS/route dependencies (TASK-003).
- Backup coverage per service and whether a PBS restore actually works (TASK-003, TASK-004).
- Which machine is the "remaining spare machine" for the new compute environment (M004).
