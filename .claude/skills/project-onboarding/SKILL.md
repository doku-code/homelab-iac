---
name: project-onboarding
description: Orient yourself in a harness-managed project at the start of a session or after context compaction, reading the smallest durable state (status, the one relevant task) instead of the documentation tree. Use when starting work, when unsure of project state, or when asked "where were we".
metadata:
  harness: "0.1.0"
---

# Project onboarding

Goal: know enough to act, in two or three tool calls.

1. `harness status` (already injected at session start in Claude Code; do not rerun it unless the tree changed). Note the active milestone, in-progress or blocked tasks, and the verification commands.
2. If the user asked for a specific change, start it (task policy in `AGENTS.md`). Open a task only when one matches the request or the change is STANDARD/COMPLEX.
3. If resuming earlier work, open that task: its Context, Evidence and Completion summary ("Remaining:") are the checkpoint. Trust recorded evidence over memory; verify with the listed commands before continuing.
4. Open `docs/knowledge-map.md` only when you need to locate a document you do not know; read the line, then the document.

Unknown is unknown: if something was not recorded, say so instead of inventing it. `git log -n 10 --oneline` and `git status` show what changed recently.
