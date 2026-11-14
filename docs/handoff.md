---
id: GUIDE-handoff
title: Current handoff and next steps
summary: "Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task."
type: guide
status: current
importance: 5
created: 2026-11-14
updated: 2026-11-14
tags: [guide, handoff, workstation, pve-management]
related: [DOC-project-overview, ARCH-platform, ADR-009, ADR-010, ADR-012, INV-pve-management-bootstrap, M001, M002, TASK-013]
topics: [handoff, current-work, workstation, state, next-task]
---

# Current handoff and next steps

Short, current state for a new session. Vision and decisions: [project overview](project-overview.md).
Update this page when the current task changes; Git keeps the history.

## How we work (operator preference)

Build the new homelab incrementally with the infrastructure we have: deploy, migrate, reclaim the
hardware, repeat. Deliver working infrastructure in small, tested, reviewable steps; reuse existing
modules, roles and Compose files; no abstraction before it is needed. **Deliberately postponed** until
the rebuild has matured: remote OpenTofu state and locking, automated or off-site backups, a disaster
recovery design, PKI, advanced secret lifecycle. Use what exists (local state, Infisical today, TrueNAS
and PBS when a migration needs a copy). Target stack and roadmap: [project overview](project-overview.md)
(k3s first, external NVMe-backed storage, TrueNAS for backups only). Basic safety stays: plan before apply, operator approval for mutations, no
secrets or state in Git, never destroy a workload before its replacement works.

## Infrastructure now

| Item | State |
|------|-------|
| `pve-management` 192.168.0.10 | Proxmox VE 9.2, standalone for now, founding node of the new cluster; API token `/pve-management` in Infisical (env `dev`) |
| `mgmt-control-01` VM 100, 192.168.0.39 | Ubuntu Desktop 26.04.1 from the official ISO, 8 vCPU (`host`), 10 GiB, 120 GiB; OpenTofu + autoinstall + Ansible; **the operator workstation** |
| `pve-core` | Emptied (workloads moved to `pve-lab`); next to be reinstalled and joined (TASK-013) |
| `pve-lab` | Continuity host for legacy and former `pve-core` workloads: do not disrupt |
| `pve-infra`, `pve-compute` | Gone for good. Never target them |
| Legacy services | Still running (Forgejo on TrueNAS, Infisical, AdGuard 192.168.0.20, Caddy…); nothing migrated yet |

## Working from mgmt-control-01

- Access: Thincast → RDP `192.168.0.39:3389` (stage 1: `ubuntu` + RDP password; stage 2: GDM, `ubuntu`
  + Linux password). SSH `ubuntu@192.168.0.39` with the admin key works independently.
- Repository: `~/homelab-iac` on branch `main`, `origin` = Forgejo
  `https://git.doku-lab.net/Homelab/homelab-iac.git` (GitHub is a push mirror used by bootstrap only).
- Tools for user `ubuntu`: mise (Node, Python, Go, uv, Terraform, kubectl, Infisical CLI, Claude Code,
  Codex), OpenTofu, SOPS, age, Docker, `.venv` with Ansible and the harness. Zed, Obsidian, Sublime
  Merge from the GNOME app grid. The PVE root CA is in the system trust store.
- OpenTofu state for `terraform/stacks/pve-management-control` lives **only** on this VM once TASK-010's
  handoff is recorded (until then on the Mac), beside the
  code (`terraform.tfstate`, `terraform.tfvars`, mode 0600, git-ignored). The Mac copy is retired to
  the Mac's `.local/handoff/`; `make mgmt-plan` refuses to run without a state file, so an empty state
  can never try to recreate VM 100. One workstation applies at a time: this one.
- Proxmox credentials: `infisical login` once (domain `https://secrets.doku-lab.net`), then prefix
  Make targets with `infisical run --silent --env dev --path /pve-management --` and pass
  `MGMT_INPUT_SOURCE=env`.

## First steps in the first Ubuntu session

These need the operator at the keyboard (logins, tokens); do them once, in this order:

1. `claude` and `codex`: log in when prompted.
2. `infisical login` (choose the self-hosted domain above).
3. Prove state continuity before any other infrastructure change:
   `infisical run --silent --env dev --path /pve-management -- make mgmt-plan MGMT_INPUT_SOURCE=env MGMT_ALLOCATION_REVIEWED=yes`
   must report **No changes**.
4. Forgejo push access: create a personal access token in Forgejo (repository read/write), then
   `git config --global credential.helper store`; the first `git push` asks for the user and the
   token and stores them in `~/.git-credentials` (0600).

## Current and next work

- **M001 (active)**: management workstation. Remaining: the operator's Thincast login and the first
  Ubuntu session above, then close M001 (TASK-006/008/009/010).
- **Next: M002, [TASK-013](../tasks/TASK-013-reinstall-pve-core-and-form-cluster.md)**: inventory
  `pve-core`'s NVMe, guard its legacy roots, reinstall Proxmox, create the cluster on `pve-management`
  and join `pve-core` (each live step approved). Then M003 runner, M004 k3s, M005 Headlamp.

## Commands

| Purpose | Command |
|---------|---------|
| Project state | `.venv/bin/harness status` |
| Offline checks | `make mgmt-check` (all checks: `harness.yaml` verification commands) |
| Re-apply workstation config (idempotent) | `make mgmt-configure MGMT_CONFIGURE_APPROVED=yes MGMT_SOURCE_COMMIT=<full sha on the GitHub mirror>` from a machine that can SSH to 192.168.0.39 |
| Add a workstation tool | one line in `ansible/roles/admin_workstation/defaults/main.yml`, then re-apply |

## Known issues

- DNS has a single server (AdGuard 192.168.0.20); when it is down, internal names such as Infisical and
  package downloads fail.
- Four legacy roots still point at `192.168.0.10`; Make refuses them (legacy inventory). Two legacy
  states record retired `pve-compute` guests.
- GDM allows one graphical session per user: log out of a Proxmox console desktop before RDP.
- Docker-published ports bypass `ufw`; bind development containers to `127.0.0.1`.
