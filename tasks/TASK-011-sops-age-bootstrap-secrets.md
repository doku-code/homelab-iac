---
id: TASK-011
title: "SOPS + age bootstrap secrets"
summary: "Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows."
type: task
status: planned
priority: critical
milestone: M012
created: 2026-11-12
updated: 2026-11-14
tags: [secrets, sops, age]
depends_on: [TASK-006]
related: [ARCH-platform]
related_decisions: [ADR-004]
related_implementations: []
related_tests: []
tests_justification: ""
verification_commands: []
evidence: []
---

# TASK-011 — SOPS + age bootstrap secrets

> Deferred by the operator on 2026-11-14: not a prerequisite for the rebuild (moved from M001 to M012, backups and finalization).

**Authorization:** OFFLINE_CODE; key generation by the operator. A task status never authorizes a live change by itself.

## Goal

Bootstrap works when Phase, Forgejo and Windmill are unavailable.

## Context

- [ADR-004](../docs/decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)

## Acceptance criteria

- [ ] age recipients documented; private keys held by the operator outside the homelab
- [ ] CI validation never receives the age key
- [ ] A workstation can decrypt and run a plan

## Verification

- sops --decrypt test with a throwaway key in tests
- gitleaks clean

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
