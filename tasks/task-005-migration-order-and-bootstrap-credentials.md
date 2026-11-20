---
title: TASK-005 — Migration order and bootstrap credential requirements
description: Decide the service migration order and list every bootstrap credential and recovery prerequisite.
published: true
tags:
- task
- planned
- planning
- migration
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-005 — Migration order and bootstrap credential requirements

> **ID:** TASK-005 · **Type:** task · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-005-migration-order-and-bootstrap-credentials.md)

> Roadmap 2026-11-14: moved from M000 to M010.

**Authorization:** READ_ONLY. A task status never authorizes a live change by itself.

## Goal

Turn the inventory into an executable migration sequence.

## Context

- TASK-002..004
- [ADR-001](/docs/decisions/adr-001-rolling-infrastructure-rebuild)
- [ADR-004](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap)

## Acceptance criteria

- [ ] Ordered migration list with rationale, downtime and rollback per service
- [ ] Bootstrap credential list (names, owners, storage location type — no values)
- [ ] Hardware reclaim order (which host empties first)

## Verification

- Operator review

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
