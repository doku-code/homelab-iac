---
title: TASK-007 — Scoped Proxmox API token and SSH access for pve-management
description: Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible.
published: true
tags:
- task
- completed
- pve-management
- access
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-007 — Scoped Proxmox API token and SSH access for pve-management

> **ID:** TASK-007 · **Type:** task · **Status:** completed · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-007-pve-management-access.md)

**Authorization:** LIVE_CHANGE — operator creates the identity; agent verifies read-only. A task status never authorizes a live change by itself.

## Goal

Automation can reach pve-management with least privilege; nothing is assumed to exist.

## Context

- [ADR-002](/docs/decisions/adr-002-pve-management-standalone-host)
- Readiness and required privileges: [INV-pve-management-bootstrap](/docs/investigations/pve-management-bootstrap)

## Acceptance criteria

- [x] Documented exact role/privilege list per ACL path (PVE API schema)
- [x] Token created by the operator and stored in Infisical (`/pve-management`); SOPS copy remains TASK-011
- [x] Token reads `/version` and `/nodes` with TLS verified against the host CA
- [x] Storages (incl. `import` content), bridge and free VMID recorded; the VM address is chosen in TASK-008
- [x] Reachability of 8006/tcp and 22/tcp from the workstation recorded; CT301 is out of scope (ADR-008)

## Verification

- `make mgmt-discover` with the token and the host CA (read-only); the first `tofu plan` belongs to TASK-008

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Ports 8006/22 reachable from the workstation | PASS (TCP connect) | read-only check | 2026-11-12 |
| TLS certificate inspected | Self-signed PVE CA, SANs include 192.168.0.10 and pve-management; not yet trusted | INV-pve-management-bootstrap | 2026-11-12 |
| Identity/token created; `make mgmt-discover` with verified TLS | PASS: PVE 9.2.26 standalone, no missing privileges, no refused requests | INV-pve-management-bootstrap | 2026-11-14 |

## Completion summary

Dedicated least-privilege identity `tofu@pve!mgmt` created by the operator and verified read-only with TLS against the host CA on 2026-11-14; all required privileges present, nothing granted on `/`.
