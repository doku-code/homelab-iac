---
id: GUIDE-handoff
title: Current handoff and next steps
summary: "Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task."
type: guide
status: current
importance: 5
created: 2026-11-14
updated: 2026-11-16
tags: [guide, handoff, workstation, pve-management]
related: [DOC-project-overview, ARCH-platform, ADR-009, ADR-010, ADR-012, ADR-014, INV-new-proxmox-cluster-inventory, INV-legacy-inventory, INV-pve-management-bootstrap, M001, M003]
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
| New cluster `doku-lab` | Proxmox VE 9.2, quorate, 4 nodes: `pve-management` .10, `pve-core` .11, `pve-infra` .12, new `pve-lab` .16 ([inventory](investigations/new-proxmox-cluster-inventory.md)); only VM 100 exists |
| `mgmt-control-01` VM 100, 192.168.0.39 on `pve-management` | Ubuntu Desktop 26.04.1, 8 vCPU, 10 GiB, 120 GiB; OpenTofu + autoinstall + Ansible; **the operator workstation and the only OpenTofu executor** |
| Old environment: `pve-lab` **192.168.0.14** | Ryzen 9 9950X3D, independent, runs the legacy services; never join, rename or reconfigure it. Future `pve-compute` after M010 |
| Legacy services | Still running (Forgejo on TrueNAS, Infisical, AdGuard 192.168.0.20, Caddy 192.168.0.24…); nothing migrated yet |

Two hosts are named `pve-lab` and `pve-lab.doku-lab.net` resolves to the old side's proxy (.24): **always
use IPs**. The new nodes have no DNS records.

## Working from mgmt-control-01

- Access: Thincast → RDP `192.168.0.39:3389`, colour depth **32 bit** and connection type LAN/auto
  (GNOME refuses clients without the RDP graphics pipeline). Stage 1: `ubuntu` + RDP password; stage 2: GDM,
  `ubuntu` + Linux password. Log out of the Proxmox console session first (one GNOME session per user).
  SSH `ubuntu@192.168.0.39` with the admin key works independently. Passwords: `.local/mgmt-control/`.
- SSH from the workstation: its own key `~/.ssh/id_ed25519` (public part `keys/mgmt-control-01.pub`) logs in
  as `ubuntu` on itself and as `root` on the four new nodes (cluster-wide `authorized_keys`). Not on `.14`.
- Repository: `~/homelab-iac`, branch `main`, `origin` = Forgejo `https://git.doku-lab.net/Homelab/homelab-iac.git`,
  `github` = push mirror (used by `mgmt-configure` as an independent source).
- Tools for `ubuntu` (interactive shells, via mise): Node, Python, Go, uv, Terraform, kubectl, Helm,
  Infisical CLI, Claude Code, Codex; plus OpenTofu, SOPS, age, Docker, Git, `.venv` with Ansible and the
  harness. Zed, Obsidian, Sublime Merge in the GNOME app grid. The PVE root CA is trusted system-wide.
- OpenTofu state for `terraform/stacks/pve-management-control` lives **only here**, beside the code
  (`terraform.tfstate`, `terraform.tfvars`, 0600, git-ignored); handed over 2026-11-16, plan from here: no
  changes. The Mac copy is retired (Mac `.local/handoff/`). `make mgmt-plan` refuses to run without a state
  file, so an empty state can never recreate VM 100.
- Legacy roots: their local states (10 roots, 22 files with private tfvars) stay in place on the Mac and
  are archived, inactive, in `.local/legacy-state-archive-2026-11-16.tar` here (0600). To work on one root
  (M010), extract only that root's files into the checkout and stop using the Mac copy; Make refuses any
  legacy root whose endpoint is a new-cluster address.
- Proxmox credentials: `infisical login` once (domain `https://secrets.doku-lab.net`), then prefix Make
  targets with `infisical run --silent --env dev --path /pve-management --` and pass `MGMT_INPUT_SOURCE=env`.
  The token sees all four nodes but has rights only on VM 100; M003 adds scoped identities.
- Read-only cluster audit outputs: `.local/audit/2026-11-16/`.

## First steps in the first Ubuntu session

These need the operator at the keyboard (logins, tokens); do them once, in this order:

1. `claude` and `codex`: log in when prompted.
2. `infisical login` (choose the self-hosted domain above).
3. Prove state continuity with your own session:
   `infisical run --silent --env dev --path /pve-management -- make mgmt-plan MGMT_INPUT_SOURCE=env MGMT_ALLOCATION_REVIEWED=yes`
   must report **No changes**.
4. Forgejo push access: create a personal access token in Forgejo (repository read/write), then
   `git config --global credential.helper store`; the first `git push` asks for the user and the
   token and stores them in `~/.git-credentials` (0600).

## Current and next work

- **M001**: closes once the Thincast two-stage login is confirmed (TASK-009); everything else is verified.
- **M002 completed**: cluster formed by the operator, audited read-only.
- **Next: M003, dedicated Forgejo deployment runner** ([ADR-014](decisions/ADR-014-dedicated-forgejo-deployment-runner.md)):
  a runner VM (OpenTofu `headless-vm` module, proposed on `pve-infra` .12) and Ansible role, registered with
  the existing Forgejo, approval-gated workflows, scoped Proxmox credentials; CT301 gets none. Start with a
  task (`harness new task`), a plan, and operator approval before any apply. Then M004 k3s (first server on
  `pve-lab` .16), M005 Headlamp, M006 storage.

## Commands

| Purpose | Command |
|---------|---------|
| Project state | `.venv/bin/harness status` |
| Offline checks | `make mgmt-check` (all checks: `harness.yaml` verification commands) |
| Re-apply workstation config (idempotent, runs from the workstation itself) | `make mgmt-configure MGMT_CONFIGURE_APPROVED=yes MGMT_SOURCE_COMMIT=<full sha on the GitHub mirror>` |
| Add a workstation tool | one line in `ansible/roles/admin_workstation/defaults/main.yml`, then re-apply |
| Reinstall VM 100 in place | `terraform/stacks/pve-management-control/README.md` |
| Read a node | `ssh root@192.168.0.1x` (IPs only) |

## Known issues

- DNS has a single server (AdGuard 192.168.0.20); when it is down, internal names such as Infisical and
  package downloads fail.
- `pve-management` runs kernel 7.0.14-28, the other nodes -29: reboot it during approved maintenance.
- One corosync link on the shared 1 GbE LAN, one SSD per node: no physical HA yet.
- GDM allows one graphical session per user: log out of a Proxmox console desktop before RDP.
- Docker-published ports bypass `ufw`; bind development containers to `127.0.0.1`.
