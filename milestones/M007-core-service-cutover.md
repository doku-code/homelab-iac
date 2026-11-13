---
id: M007
title: "Core service cutover and retirement"
summary: "Foundational services run on the new platform, recovery works without the original cluster, and the old environment is decommissioned."
type: milestone
status: planned
priority: medium
created: 2026-11-12
updated: 2026-11-12
tags: [cutover, retirement]
related_tasks: []
related_decisions: [ADR-001]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M007 — Core service cutover and retirement

## Objective

Make the new infrastructure fully independent.

**Completion criterion:** Foundational services run on the new platform, recovery works without the original cluster, and the old environment is decommissioned.

## Scope

In scope:

- Migrate Forgejo, identity, reverse proxy, DNS and management components
- Recovery test without the original cluster
- Decommission the old environment after all data is migrated

Out of scope:

-

## Expected deliverables

- Recovery test report
- Decommission checklist

## Dependencies

- M005
- M006

## Acceptance criteria

- [ ] Full recovery exercised without the original cluster
- [ ] No service or data left on the old environment

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
