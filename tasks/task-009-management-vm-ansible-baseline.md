---
title: TASK-009 — Ansible baseline for the management VM (toolchain and runner)
description: 'Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008).'
published: true
tags:
- task
- completed
- ansible
- runner
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-009 — Ansible baseline for the management VM (toolchain and runner)

> **ID:** TASK-009 · **Type:** task · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-009-management-vm-ansible-baseline.md)

**Authorization:** LIVE_CHANGE with approval. A task status never authorizes a live change by itself.

## Goal

The management VM can run IaC workflows itself.

## Context

- TASK-008
- Legacy `ansible/roles/guest_base` and `forgejo_runner` as references

## Acceptance criteria

- [x] Role(s) converge with changed=0 on the second run
- [x] Toolchain versions reported (OpenTofu, SOPS, age) and `pip check` clean
- [x] No runner installed in M001; a trusted runner is a later, separate decision (ADR-008)
- [x] GNOME desktop, graphical target, interactive one-time login password (ADR-009)
- [x] Developer catalog installed: apt tools + Docker, Flathub (Zed, Obsidian, Sublime Merge), mise runtimes and CLIs incl. Claude Code and Codex
- [x] RDP remote login works from the Thincast client through both stages; second run reports no changes and resets no credential
- [x] RDP refused outside the allowed networks; SSH and the Proxmox console work without RDP

## Verification

- ansible-playbook --syntax-check
- --check --diff
- Two live convergence runs

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/mgmt-control.py` | role syntax, catalog sanity, secrets under no_log | `make mgmt-check` | PASS (2026-11-14) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `ansible-playbook --syntax-check` (legacy and synthetic inventory) | PASS | local run | 2026-11-12 |
| `admin_workstation` role: static syntax check + catalog sanity (pinned mise key, Flathub IDs, no piped installers, secrets under no_log) | PASS | tests/mgmt-control.py | 2026-11-14 |
| Live convergence on the reinstalled Desktop (passwords from `.local/mgmt-control/`) | Run 1 at 0e08b10: ok=49 changed=29 failed=0, but RDP credentials stayed empty (grdctl needs a terminal). Fixed in 6c40081 (`script` pty); run 2: changed=2 (credentials + restart), stored RDP password matches the file | `make mgmt-configure`, `grdctl --system status` | 2026-11-14 |
| Idempotency | Run 3: ok=41 changed=0 failed=0, no ACTION REQUIRED | `make mgmt-configure` | 2026-11-14 |
| Tools as `ubuntu` | claude 2.1.325, codex 0.169.0, node 26.13.1, Python 3.13.18, go 1.27.4, uv 0.13.8, terraform 1.16.1, kubectl 1.35.8, infisical 0.45.8, tofu 1.13.9, sops 3.13.3, age 1.2.1, docker 29.1.3, git 2.53.0, ansible-core 2.21.6, harness; flatpaks Zed, Obsidian, Sublime Merge; GDM and gnome-remote-desktop active; PVE CA trusted; ufw 22 any, 3389 from 192.168.0.0/24 | SSH checks | 2026-11-14 |
| Thincast two-stage login | PASS: stage 1 `ubuntu` + RDP password, stage 2 GDM `ubuntu` + Linux password, desktop usable; resolution and scale follow the client ("Auto-fit window and session", 32-bit colour) | operator, Thincast client | 2026-11-17 |
| RDP outside allowed networks | Not tested from outside the LAN. Covered by configuration: ufw active, default deny incoming, 3389/tcp allowed only from 192.168.0.0/24; SSH 22/tcp independent of RDP | `sudo ufw status verbose` | 2026-11-17 |
| Toolchain recheck | tofu 1.13.9, sops 3.13.3, age 1.2.1, codex 0.169.0; `pip check`: no broken requirements; `git ls-remote origin` reaches Forgejo | local run | 2026-11-17 |

## Completion summary

Completed 2026-11-17. The workstation converges idempotently from Ansible, the toolchain works as
`ubuntu`, and the operator confirmed the Thincast two-stage login. The "RDP refused outside the allowed
networks" criterion is verified from the ufw ruleset, not by a connection attempt from another network.
No runner on this VM (dedicated runner: M003).
