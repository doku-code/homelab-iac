---
name: task-execution
description: Execute a STANDARD or COMPLEX change end to end with verified evidence - reuse or create the task, implement with tests, run verification, record evidence and status truthfully. Use when implementing a feature, resuming an in-progress task, or when asked to "do TASK-xxx". SIMPLE changes do not need this skill.
metadata:
  harness: "0.1.0"
---

# Task execution

Classify first (task policy in `AGENTS.md`): a SIMPLE change is implemented directly with its relevant tests and needs no task document.

## Before implementing (STANDARD / COMPLEX)

1. Reuse the matching task from `harness status`; otherwise `harness new task "<title>" --summary "<one line>"` with `milestone`, `priority`, `depends_on`. Set `status: in-progress`.
2. Retrieve only what the change needs (`context-retrieval`). List reusable code and documents under Context.
3. Write the acceptance criteria and the exact verification commands before coding, and decide which tests will prove the change (follow the testing conventions in `AGENTS.md`).

## Implement

- Smallest sound change that meets the criteria. Tests ship with the code; list every test file in `related_tests` and fill the task's Tests table.
- Sensitive values stay in `.local/`.

## Verify and record

1. Run the new tests alone, then the verification commands. Paste only the decisive lines into the Tests and Evidence tables with the date.
2. A failing command is recorded as a failure; unverified work is "not verified".
3. Status: `completed` only when every criterion has evidence; `in-progress` with a "Remaining:" line in the Completion summary for partial work (this line is the checkpoint a fresh session resumes from); `blocked` with the blocker.
4. If a criterion closes a milestone, update the milestone's Verification evidence. Record a real tradeoff with `harness new decision`; a failed approach with `harness new failed-implementation`.
5. Commit with a Conventional Commit message that names the task (`feat(auth): add token refresh (TASK-012)`). Do not add a commit to document that commit; `harness history sync` is optional and only for commits worth annotating.
6. `harness check` before the final commit (or let the pre-commit hook do it).

## Scope discipline

Do the task you were given. Note newly discovered work as planned tasks instead of doing it.
