---
id: TASK-009
title: "Ansible baseline for the management VM (toolchain and runner)"
summary: "Configure the management VM with Ansible: SSH hardening, guest agent, OpenTofu, Ansible environment, SOPS/age. No runner in M001 (ADR-008)."
type: task
status: in-progress
priority: high
milestone: M001
created: 2026-11-12
updated: 2026-11-14
tags: [ansible, runner]
depends_on: [TASK-008, TASK-011]
related: [ARCH-platform]
related_decisions: [ADR-002]
related_implementations: []
related_tests: [tests/mgmt-control.py]
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-009 — Ansible baseline for the management VM (toolchain and runner)

**Authorization:** LIVE_CHANGE with approval. A task status never authorizes a live change by itself.

## Goal

The management VM can run IaC workflows itself.

## Context

- TASK-008
- Legacy `ansible/roles/guest_base` and `forgejo_runner` as references

## Acceptance criteria

- [ ] Role(s) converge with changed=0 on the second run
- [ ] Toolchain versions reported (OpenTofu, SOPS, age) and `pip check` clean
- [x] No runner installed in M001; a trusted runner is a later, separate decision (ADR-008)
- [ ] GNOME desktop, graphical target, interactive one-time login password (ADR-009)
- [ ] Developer catalog installed: apt tools + Docker, Flathub (Zed, Obsidian, Sublime Merge), mise runtimes and CLIs incl. Claude Code and Codex
- [ ] RDP remote login works from the Thincast client through both stages; second run reports no changes and resets no credential
- [ ] RDP refused outside the allowed networks; SSH and the Proxmox console work without RDP

## Verification

- ansible-playbook --syntax-check
- --check --diff
- Two live convergence runs

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `ansible-playbook --syntax-check` (legacy and synthetic inventory) | PASS | local run | 2026-11-12 |
| `admin_workstation` role: static syntax check + catalog sanity (pinned mise key, Flathub IDs, no piped installers, secrets under no_log) | PASS | tests/mgmt-control.py | 2026-11-14 |
| Live convergence on the reinstalled Desktop (passwords from `.local/mgmt-control/`) | Run 1 at 0e08b10: ok=49 changed=29 failed=0, but RDP credentials stayed empty (grdctl needs a terminal). Fixed in 6c40081 (`script` pty); run 2: changed=2 (credentials + restart), stored RDP password matches the file | `make mgmt-configure`, `grdctl --system status` | 2026-11-14 |
| Idempotency | Run 3: ok=41 changed=0 failed=0, no ACTION REQUIRED | `make mgmt-configure` | 2026-11-14 |
| Tools as `ubuntu` | claude 2.1.325, codex 0.169.0, node 26.13.1, Python 3.13.18, go 1.27.4, uv 0.13.8, terraform 1.16.1, kubectl 1.35.8, infisical 0.45.8, tofu 1.13.9, sops 3.13.3, age 1.2.1, docker 29.1.3, git 2.53.0, ansible-core 2.21.6, harness; flatpaks Zed, Obsidian, Sublime Merge; GDM and gnome-remote-desktop active; PVE CA trusted; ufw 22 any, 3389 from 192.168.0.0/24 | SSH checks | 2026-11-14 |
| Thincast two-stage login | not verified (operator) | — | — |

## Completion summary

_Not completed._
