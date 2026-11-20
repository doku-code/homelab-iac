---
title: M008 — Phase
description: Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it.
published: true
tags:
- milestone
- active
- roadmap
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M008 — Phase

> **ID:** M008 · **Type:** milestone · **Status:** active · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M008-phase.md)

## Objective

Replace Infisical progressively once a working alternative exists.

**Completion criterion:** Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it.

## Scope

In scope:

- Validate self-hosted licensing, chart, external PostgreSQL support and Authentik integration
- Deploy, create service identities, integrate CI and Kubernetes
- Migrate secrets incrementally; Infisical stays until consumers moved

Out of scope:

- Dynamic database credentials or automatic rotation as goals
- Blocking the rebuild on a full migration

## Expected deliverables

- Phase deployment values, identity model, migration checklist

## Dependencies

- M007

## Acceptance criteria

- [ ] A new deployment consumes a secret from Phase
- [x] Infisical consumers listed with their migration state (TASK-019, 2026-11-17)

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
