---
name: documentation-maintenance
description: Keep project knowledge accurate after an implementation change - find affected documents, update the authoritative ones, record decisions, refresh evidence, regenerate indexes and validate. Use after code changes, when docs and code disagree, or when asked to "update the docs".
metadata:
  harness: "{{harness_version}}"
---

# Documentation maintenance

Proportional to the change. A bug fix usually touches one task file; a new component touches an architecture document and possibly an ADR.

## Procedure

1. Identify affected components (paths you changed). Find their documents: `harness docs search --impl <path>` and `harness docs search --component <name>`.
2. Decide what changed:
   - behaviour or architecture → update the authoritative architecture/component document (`updated: today`); add a short "Changed in <commit/task>" note if the change is significant.
   - a tradeoff decision → `harness new decision` (status `accepted`); if it replaces an older ADR set `supersedes`/`superseded_by`, do not edit the old ADR's content.
   - external behaviour learned → create or update the reference under `{{references_dir}}/` (version, verification date).
   - operational procedure → runbook/deployment/troubleshooting document.
3. Update the task's Evidence and Completion summary; update milestone evidence if a criterion was met.
4. Regenerate: `harness docs index` (the pre-commit hook does it when installed).
5. Validate: `harness check` must report no errors. Fix broken links and unknown IDs it lists.
6. Staleness: `harness context review` lists documents whose `review_after` passed, whose `source_paths` changed after
   `last_verified`, or that reference superseded documents. Review the content, correct it, then
   `harness context verify <ID> --review-after-days 90` (add `--mark-active` to clear `needs-review`). Never verify
   a document you did not read against the code.

## Rules

- One authoritative location per fact. Link, do not copy.
- Historical documents (ADRs, reports, history records) are snapshots. Correct the current document and link the correction; do not rewrite history.
- Do not create documents that merely restate code. Document intent, decisions, constraints and verification.
- Do not generate documents because a template exists. Create a document only when the knowledge would otherwise be lost.
- Never mark something verified that you did not observe.
- Frontmatter `id` values are permanent; renaming a file is fine, changing an `id` is not.
