---
title: TASK-011 — SOPS + age bootstrap secrets
description: Introduce .sops.yaml, an encrypted secrets/bootstrap/ file for the Proxmox token and SSH material, and decryption in Ansible/OpenTofu workflows.
published: true
tags:
- task
- planned
- secrets
- sops
- age
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-011 — SOPS + age bootstrap secrets

> **ID:** TASK-011 · **Type:** task · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-011-sops-age-bootstrap-secrets.md)

> Deferred by the operator on 2026-11-14: not a prerequisite for the rebuild (moved from M001 to M012, backups and finalization).

**Authorization:** OFFLINE_CODE; key generation by the operator. A task status never authorizes a live change by itself.

## Goal

Bootstrap works when Phase, Forgejo and Windmill are unavailable.

## Context

- [ADR-004](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap)

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
