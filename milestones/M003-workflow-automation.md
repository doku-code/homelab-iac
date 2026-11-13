---
id: M003
title: "Workflow automation (Windmill)"
summary: "A Windmill workflow initiates an approved IaC operation from a service-catalog form and reports its outcome."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-12
tags: [windmill, automation]
related_tasks: []
related_decisions: [ADR-005]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M003 — Workflow automation (Windmill)

## Objective

Introduce Windmill as the operational automation interface over versioned workflows.

**Completion criterion:** A Windmill workflow initiates an approved IaC operation from a service-catalog form and reports its outcome.

## Scope

In scope:

- Windmill in a dedicated environment with persistent storage and backups
- Forgejo integration and Git-synced scripts
- Forms generated from services/<service>/service.yaml
- Execution logging and failure reporting

Out of scope:

- Infrastructure definitions inside Windmill
- Windmill as a recovery dependency

## Expected deliverables

- services/windmill definition
- windmill/ scripts and flows in Git
- First catalog-driven deployment workflow

## Dependencies

- M001
- M002 for secret retrieval (Infisical acceptable meanwhile)

## Acceptance criteria

- [ ] A Windmill run triggers an approved deployment workflow and shows its result
- [ ] The same deployment runs without Windmill
- [ ] Windmill data restored from backup

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
