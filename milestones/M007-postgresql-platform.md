---
id: M007
title: "PostgreSQL platform"
summary: "The selected PostgreSQL operator runs a Patroni-managed primary on external NVMe-backed storage, with per-application databases and roles."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-14
tags: [roadmap]
related_tasks: []
related_decisions: [ADR-013, ADR-012]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M006]
completion_criteria: []
---

# M007 — PostgreSQL platform

## Objective

Provide the shared relational database for Phase, Windmill, Authentik and applications.

**Completion criterion:** The selected PostgreSQL operator runs a Patroni-managed primary on external NVMe-backed storage, with per-application databases and roles.

## Scope

In scope:

- Validate the Zalando Postgres Operator (version, k3s and storage compatibility)
- Patroni primary on an NVMe-backed PVC; standbys prepared for later hosts
- Databases and roles per application, credentials outside Git

Out of scope:

- Active data on TrueNAS
- Using this PostgreSQL as the k3s datastore

## Expected deliverables

- Operator manifests or chart values, database/role definitions

## Dependencies

- M006

## Acceptance criteria

- [ ] A test database survives pod rescheduling
- [ ] Per-application role isolation verified

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
