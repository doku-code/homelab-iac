---
name: implementation-review
description: Verify that claimed work really exists and works - check tasks and milestones against code, tests, Git history and documentation, and correct status and evidence. Use before marking a milestone completed, when reviewing another agent's work, before a release, or when asked to audit progress.
metadata:
  harness: "0.1.0"
---

# Implementation review

Evidence before assertions. The review produces corrected task/milestone state, not opinions.

## Procedure

1. `harness status` and `harness check` — note errors, stale indexes and open tasks.
2. For each task under review:
   - Read its acceptance criteria and Evidence table.
   - Confirm each referenced implementation path exists and does what the criterion says (read the code).
   - Re-run the verification commands listed in the task (or `harness.yaml`). Record the observed result and date in the Evidence table.
   - Confirm referenced commits exist: `git log --oneline -n 1 <sha>`; check `history/` records are annotated truthfully (reason and verification match reality).
   - Correct status: downgrade `completed` work without evidence to `in-progress` and list what is missing.
3. For a milestone: every acceptance criterion needs a row in Verification evidence with an observed result. Otherwise it stays `active`/`blocked` with the gap written in the Completion summary.
4. Check documentation drift: architecture documents and references touched by the implementation must still match the code (`harness docs search --impl <path>`). File corrections through the `documentation-maintenance` skill.
5. Check safety: `harness check` sensitive-data section passes; nothing from `.local/` is tracked; no secrets in docs or examples.
6. Write findings as a short list (what was verified, what was corrected, what remains). If the review is substantial, record it with `harness new testing-report` or `harness new task-report`.

## Rules

- A green test you did not run is not evidence. A diff is evidence of change, not of correctness.
- Prefer re-running the smallest decisive command over trusting a log.
- Never "fix" the state by editing evidence; fix the implementation or the status.
