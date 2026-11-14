---
id: TASK-007
title: "Scoped Proxmox API token and SSH access for pve-management"
summary: "Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible."
type: task
status: completed
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-14
tags: [pve-management, access]
depends_on: [TASK-001]
related: [ARCH-platform]
related_decisions: [ADR-002]
related_implementations: []
related_tests: []
tests_justification: "Live access verification task with no implementation paths; the discovery script it exercised is covered by tests/mgmt-control.py."
verification_commands: []
evidence: []
---

# TASK-007 — Scoped Proxmox API token and SSH access for pve-management

**Authorization:** LIVE_CHANGE — operator creates the identity; agent verifies read-only. A task status never authorizes a live change by itself.

## Goal

Automation can reach pve-management with least privilege; nothing is assumed to exist.

## Context

- [ADR-002](../docs/decisions/ADR-002-pve-management-standalone-host.md)
- Readiness and required privileges: [INV-pve-management-bootstrap](../docs/investigations/pve-management-bootstrap.md)

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
