@AGENTS.md

<!-- harness:managed:start v=0.1.0 -->
## Claude Code notes

- Project instructions are in `AGENTS.md`, imported above. Do not duplicate them here; add Claude-specific notes outside this block.
- Skills: `/project-onboarding`, `/context-retrieval`, `/task-execution`, `/documentation-maintenance`, `/technical-research`, `/implementation-review`.
- Path-scoped rules in `.claude/rules/` apply when editing documents under `docs/`, `milestones/`, `tasks/` or `history/`.
- A `SessionStart` hook injects `harness status --brief` when the `harness` CLI is on PATH; otherwise run it yourself.

### Delegation (native subagents only)

You are the primary agent: you read the documentation path, pick the task, implement, integrate, validate, document. Subagents are optional helpers, not a team.

- Available: `harness-context-retriever` and `harness-code-reviewer` (file tools only, no shell: they cannot write or run anything; pass the reviewer the changed paths or the diff), `harness-test-runner` (has a shell, restricted by instruction to the recorded verification commands), `harness-implementer` (may edit; only with a precise brief listing the files it may touch).
- Limits enforced by `.claude/settings.json`: at most 3 concurrent subagents, spawn depth 1 (subagents cannot delegate). Budget by convention: at most 4 delegations per task; stop delegating once the evidence is sufficient.
- Delegate only genuinely independent work with a defined objective and expected output; SIMPLE and most STANDARD changes run directly here (task policy in `AGENTS.md`). Reuse findings already in `docs/`, tasks and history before researching again. No verification swarms: automated tests are the validation; a review is supplementary.
- Integrate subagent results yourself, run the verification commands, then update the task and documentation with observed outcomes and unresolved blockers.
<!-- harness:managed:end -->

## Project notes (homelab-iac)

- The harness CLI lives in the repository environment: run `.venv/bin/harness …` (the SessionStart hook does this).
- `harness update` reports `.forgejo/workflows/harness-docs-validate.yml` as a conflict on purpose (main-only
  gate, `homelab-iac` runner); keep that adaptation. It also re-creates `harness-wiki-publish.yml`; delete it.
- Keep delegation light: one coordinating agent, at most 2–4 subagents and only for independent work; no review
  or report ceremony that does not change a decision.
