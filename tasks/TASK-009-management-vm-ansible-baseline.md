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
| Two live convergence runs | not verified (VM not provisioned) | — | 2026-11-12 |

## Completion summary

_Not completed._
