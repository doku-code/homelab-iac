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
depends_on: [TASK-002]
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
- TASK-002 network facts

## Acceptance criteria

- [ ] Documented role/privilege list for the automation user
- [ ] Token created by the operator and stored as a bootstrap secret (TASK-011)
- [ ] Read-only API call and SSH connection verified from the existing runner and from a workstation

## Verification

- `tofu plan` against an empty root succeeds with the token

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| | not verified | | |

## Completion summary

_Not completed._
