---
id: TASK-007
title: "Scoped Proxmox API token and SSH access for pve-management"
summary: "Define and verify the dedicated automation identity, role and token on pve-management, and SSH access for Ansible."
type: task
status: planned
priority: critical
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [pve-management, access]
depends_on: [TASK-001]
related: [ARCH-platform]
related_decisions: [ADR-002]
related_implementations: []
related_tests: []
tests_justification: ""
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
- [ ] Token created by the operator and stored as a bootstrap secret (TASK-011)
- [ ] Token reads `/version` and `/nodes` with TLS verified (pinned CA or trusted certificate)
- [ ] Storages (incl. `import` content), bridge, free VMID and the management VM address recorded
- [ ] Reachability of 8006/tcp and 22/tcp from the workstation and from CT301 recorded

## Verification

- `tofu plan` against an empty root succeeds with the token

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Ports 8006/22 reachable from the workstation | PASS (TCP connect) | read-only check | 2026-11-12 |
| TLS certificate inspected | Self-signed PVE CA, SANs include 192.168.0.10 and pve-management; not yet trusted | INV-pve-management-bootstrap | 2026-11-12 |
| Identity/token created; API read with verified TLS | not verified (operator action pending) | — | 2026-11-12 |

## Completion summary

_Not completed._
