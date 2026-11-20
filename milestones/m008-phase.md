---
title: M008 — Phase
description: Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M008 — Phase

> **ID:** M008 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M008-phase.md)

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

- [x] A new deployment consumes a secret from Phase
- [x] Infisical consumers listed with their migration state (TASK-019, 2026-11-17)

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| A new deployment consumes a secret from Phase | `make wiki-secrets`, then `scripts/secrets.py run /wiki /postgresql -- make wiki-deploy` ([TASK-029](/tasks/task-029-wiki-js-3-on-k3s-showing-this-repository-s-documentation)) | The wiki's administrator and database passwords were generated into Phase and read from it at deployment; never printed, never in Git. Same path for the dashboard ([TASK-027](/tasks/task-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab)) and the Proxmox sign-in secret | 2026-11-20 |
| Infisical consumers listed | [TASK-019](/tasks/task-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i) | Listed with their migration state; Infisical is stopped | 2026-11-17 |

## Completion summary

Completed 2026-11-20: Phase is the store every new deployment reads its secrets from. Left to the operator, by their own choice: keeping a copy of the recovery bundle outside the homelab (TASK-019).
