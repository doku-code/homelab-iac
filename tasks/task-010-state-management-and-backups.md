---
title: TASK-010 — OpenTofu state management and backups
description: Keep new-root state local on the single operator workstation, move it from the Mac to mgmt-control-01, and never let an empty state recreate existing guests.
published: true
tags:
- task
- completed
- state
- backup
editor: markdown
date: '2026-11-16T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-010 — OpenTofu state management and backups

> **ID:** TASK-010 · **Type:** task · **Status:** completed · **Updated:** 2026-11-16 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-010-state-management-and-backups.md)

**Authorization:** LIVE_CHANGE (backup storage) with approval. A task status never authorizes a live change by itself.

## Goal

Each root has exactly one writable state, on the operator workstation. Re-scoped by the operator on
2026-11-14: no remote backend, locking server or automated backups for now (single operator); the
legacy roots stay where they are until they are migrated.

## Context

- Nine legacy roots keep local state ([INV-legacy-inventory](/docs/investigations/legacy-inventory))
- Archived PG backend and Garage evaluations in docs/archive/codex-2026/docs/

## Acceptance criteria

- [x] `pve-management-control` state copied to `mgmt-control-01` (0600, git-ignored), Mac copy retired
- [x] `tofu state list` on the VM shows the image and VM 100; a plan from the VM reports no changes
- [x] `make mgmt-plan` refuses to run without a state file (tested in `tests/mgmt-control.py`)

## Verification

- `tofu state list` and a no-change `make mgmt-plan` on the VM

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Bootstrap strategy for new roots: local state + `mgmt-state-backup` (age, off-machine) | Implemented; refusal paths tested; no state exists yet | Makefile, ARCH-platform#state-management | 2026-11-12 |
| Backups of the nine legacy local states | Deferred by the operator (re-scope above) | — | 2026-11-14 |
| Handoff to `mgmt-control-01` | `terraform.tfstate` + private `terraform.tfvars` copied over SSH, SHA-256 identical on both sides, mode 0600, owner `ubuntu`, ignored by Git | `sha256sum`, `git status` | 2026-11-16 |
| Recognition on the VM | `tofu init` OK; `tofu state list`: `proxmox_download_file.desktop_iso`, `proxmox_virtual_environment_vm.workstation[0]`; `make mgmt-plan` from the VM: **No changes** | VM shell | 2026-11-16 |
| Mac copy retired | State, backup, tfvars and plans moved to the Mac's `.local/handoff/pve-management-control-2026-11-16/`; `make mgmt-plan` on the Mac now refuses to run | Mac shell | 2026-11-16 |

## Completion summary

Completed 2026-11-16: the only active state for `pve-management-control` is on `mgmt-control-01`; one
workstation applies. A shared backend is decided when the runner must apply (M003).
