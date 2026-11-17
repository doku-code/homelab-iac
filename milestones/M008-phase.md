---
id: M008
title: "Phase"
summary: "Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it."
type: milestone
status: active
priority: high
created: 2026-11-12
updated: 2026-11-17
tags: [roadmap]
related_tasks: [TASK-019]
related_decisions: [ADR-004, ADR-015, ADR-013, ADR-012]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M007]
completion_criteria: []
---

# M008 — Phase

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
