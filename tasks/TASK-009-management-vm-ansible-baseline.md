---
id: TASK-009
title: "Ansible baseline for the management VM (toolchain and runner)"
summary: "Configure the management VM with Ansible: users, SSH hardening, OpenTofu, Ansible, SOPS/age, CLI tools, and a dedicated Forgejo runner."
type: task
status: planned
priority: high
milestone: M001
created: 2026-11-12
updated: 2026-11-12
tags: [ansible, runner]
depends_on: [TASK-008, TASK-011]
related: [ARCH-platform]
related_decisions: [ADR-002]
related_implementations: []
related_tests: []
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
- [ ] Runner registered with a dedicated label and scoped token
- [ ] Runner registration secret handled with no_log and never committed

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
| | not verified | | |

## Completion summary

_Not completed._
