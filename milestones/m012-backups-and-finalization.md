---
title: M012 — Backups and finalization
description: Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired.
published: true
tags:
- milestone
- planned
- roadmap
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M012 — Backups and finalization

> **ID:** M012 · **Type:** milestone · **Status:** planned · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M012-backups-and-finalization.md)

## Objective

Review dependencies and recovery once the new platform has taken shape.

**Completion criterion:** Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired.

## Scope

In scope:

- Dependency and persistent-data review; backup workflows to TrueNAS
- PostgreSQL-aware backups, PBS, restore tests
- Bootstrap secrets (SOPS + age) and the recovery runbook; remote state if a second executor needs it

Out of scope:

- Destroying live data during earlier milestones (basic migration safety always applies)

## Expected deliverables

- Backup jobs, restore evidence, recovery runbook

## Dependencies

- M010

## Acceptance criteria

- [ ] A representative restore of each data class succeeded
- [ ] No workload depends on retired infrastructure

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
