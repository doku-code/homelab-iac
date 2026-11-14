---
id: M001
title: Project foundation
type: milestone
status: active
priority: high
created: {{created}}
updated: {{created}}
tags: [foundation]
related_tasks: [TASK-001]
related_decisions: []
related: []
depends_on: []
completion_criteria:
  - Project overview describes purpose, scope and structure
  - Verification commands in harness.yaml are confirmed to work
  - First real milestones and tasks are defined
---

# Project foundation

## Objective

Establish the project context an agent needs to work safely: purpose, structure, verification commands and the
first real milestones.

## Scope

In scope:

- Fill in `{{docs_dir}}/project-overview.md`.
- Confirm or correct the detected verification commands in `harness.yaml`.
- Define the next milestones and their first tasks.

Out of scope:

- Feature work.

## Expected deliverables

- Completed project overview.
- Verified `verification.commands`.
- At least one planned milestone beyond this one.

## Dependencies

- None.

## Acceptance criteria

- [ ] `harness check` passes.
- [ ] Every verification command in `harness.yaml` has been run once and marked `verified: true` (or removed).
- [ ] `harness status` shows the next milestone and task.

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| harness check passes | `harness check` | not verified | |

## Completion summary

_Not completed._
