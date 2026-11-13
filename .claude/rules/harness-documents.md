---
paths:
  - "docs/**/*.md"
  - "milestones/**/*.md"
  - "tasks/**/*.md"
  - "history/**/*.md"
---

# Knowledge document rules

- Keep the YAML frontmatter valid: `id` (stable, never renamed), `title`, `type`, `status`, `created`, `updated` (set to today when you change the document), `tags`, `related*` fields holding document IDs.
- Allowed statuses depend on type (`harness docs types`): milestones `planned|active|blocked|completed|cancelled`; tasks `planned|in-progress|blocked|completed|cancelled`; decisions `proposed|accepted|superseded|rejected|deprecated`; knowledge documents and references `active|current|draft|needs-review|superseded|archived` (plus the older `deprecated`, `needs-revalidation`).
- `completed` requires evidence rows in the Evidence / Verification evidence table (command, observed result, date). Otherwise leave the status and write "not verified".
- A completed task with `related_implementations` must list its tests in `related_tests` (paths that exist) or explain the absence in `tests_justification`.
- Optional retrieval metadata: `importance` (integer 1–5, not relevance), `topics`/`applies_to`/`source_paths` (lists), `review_after` (date). Mark replaced documents `status: superseded` with `superseded_by: [ID]`; never delete them. Do not set `last_verified` unless you reviewed the content against the code (`harness context verify <ID>`).
- Link related documents by ID in frontmatter and by relative Markdown link in the body. Do not paste content from other documents; link to them.
- Files under `history/` keep their derived block (`harness:derived:start/end`) untouched; write only in the authored sections.
- Generated files (`docs/knowledge-map.md`, `knowledge-map.json`, `history/README.md`) are never edited by hand: run `harness docs index` / `harness history sync`.
- Never write secrets, tokens, hostnames of private systems or personal data into these files; use `.local/` and reference the mechanism.
- Finish with `harness check`.
