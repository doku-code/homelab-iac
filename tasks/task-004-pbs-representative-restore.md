---
title: TASK-004 — Representative PBS restore test
description: Restore one representative guest backup from PBS to an isolated, disposable target and verify it boots and holds its data.
published: true
tags:
- task
- planned
- backup
- pbs
- recovery
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-004 — Representative PBS restore test

> **ID:** TASK-004 · **Type:** task · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-004-pbs-representative-restore.md)

> Roadmap 2026-11-14: moved from M000 to M012.

**Authorization:** LIVE_CHANGE — explicit operator approval of guest, target and network. A task status never authorizes a live change by itself.

## Goal

Prove backups are restorable before any migration relies on them.

## Context

- TASK-003 backup coverage
- PBS datastore and retention

## Acceptance criteria

- [ ] Restore to a new VMID on an isolated network, never over the original
- [ ] Boot and data check recorded; disposable guest removed only with approval

## Verification

- Restore task log and checks recorded in the evidence table

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
