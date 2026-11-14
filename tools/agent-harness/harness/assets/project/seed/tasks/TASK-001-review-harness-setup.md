---
id: TASK-001
title: Review harness setup and confirm verification commands
type: task
status: planned
priority: high
milestone: M001
created: {{created}}
updated: {{created}}
tags: [foundation]
depends_on: []
related: [DOC-project-overview]
related_decisions: []
related_implementations: [harness.yaml]
related_tests: []
tests_justification: "Configuration and documentation review; verified by `harness check`, no code to test."
verification_commands: ["harness check"]
evidence: []
---

# Review harness setup and confirm verification commands

## Goal

Make the generated harness configuration true for this project: correct profile, real verification commands,
accurate project overview.

## Context

- `harness.yaml` lists detected commands with `verified: false`. They were inferred from marker files and never run.
- `{{docs_dir}}/project-overview.md` is a draft.

## Acceptance criteria

- [ ] Each command in `verification.commands` was executed; working ones are `verified: true`, broken ones removed or fixed.
- [ ] `{{docs_dir}}/project-overview.md` has a real Purpose and Scope and status `current`.
- [ ] `harness check` reports no errors.

## Verification

```
harness check
```

## Tests

None: configuration and documentation review (see `tests_justification`).

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| harness check | not verified | | |

## Completion summary

_Not completed._
