---
id: TASK-001
title: "Reset repository to the agent harness and record the rebuild direction"
summary: "Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap."
type: task
status: in-progress
priority: critical
milestone: M000
created: 2026-11-12
updated: 2026-11-14
tags: [harness, repository]
depends_on: []
related: [ARCH-platform]
related_decisions: [ADR-007]
related_implementations: []
related_tests: [tests/stage-a-inputs.py]
tests_justification: "Documentation, agent configuration and CI wiring only; covered by harness check and scripts/check-quality.py. One pre-existing test harness fix (tests/stage-a-inputs.py) is itself a test."
verification_commands: []
evidence: []
---

# TASK-001 — Reset repository to the agent harness and record the rebuild direction

**Authorization:** OFFLINE_CODE (repository only). A task status never authorizes a live change by itself.

## Goal

Make the repository a clean, harness-managed starting point whose docs carry the agreed rebuild direction.

## Context

- Project briefing (2026-11-12) and [ARCH-platform](../docs/architecture/platform.md)
- Legacy workflow archived in [docs/archive/codex-2026](../docs/archive/codex-2026/AGENTS.md) ([ADR-007](../docs/decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md))
- Uncommitted Codex WIP (Windmill + VM208 infra runner) stashed as `stash@{0}`, not committed

## Acceptance criteria

- [ ] Harness installed (skills, agents, settings, managed blocks) and pinned in requirements-agents.txt
- [ ] CI docs validation follows the main-only activation gate; no wiki publication
- [ ] Legacy docs/tasks/roadmap/AGENTS archived with working links
- [ ] Overview, architecture, ADR-001..007, legacy inventory, milestones M000-M008 and first tasks written
- [ ] harness check and the offline verification commands pass

## Verification

- .venv/bin/harness check
- git diff --check
- .venv/bin/python scripts/check-quality.py

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `harness check` | PASS: 0 errors, 0 warnings | local run | 2026-11-12 |
| `git diff --check` | PASS | local run | 2026-11-12 |
| `scripts/check-quality.py` | PASS: 87 YAML, 24 Python, 31 shell parsed; CI gate guards hold | local run | 2026-11-12 |
| `terraform fmt -check` + `validate` on all 11 roots (backend disabled, temp TF_DATA_DIR) | PASS | local run | 2026-11-12 |
| Ansible `--syntax-check` on every playbook | PASS | local run | 2026-11-12 |
| Compose config (monitoring, windmill with synthetic input) | PASS | local run | 2026-11-12 |
| 10 offline test scripts from validate.yml | PASS after fixing pre-existing failure in tests/stage-a-inputs.py (Makefile include added in 915333c, not copied by the test) | local run | 2026-11-12 |
| `harness-docs-validate.yml` executed in Forgejo CI | FAIL run 50 on f501ff1: runner cannot fetch the private agent-harness repository (anonymous access 404) | Forgejo Actions run 50 | 2026-11-12 |
| Harness CLI vendored in `tools/agent-harness` (byte-identical to upstream `8ddf06d`), installed from `requirements-agents.txt`; read-only token approach dropped | Clean venv install + `harness check`: PASS, no access to the private template repository | local run | 2026-11-14 |
| `validate.yml` on f501ff1 | FAIL run 51 after 6 s; cause unknown, log not yet read | Forgejo Actions run 51 | 2026-11-12 |

## Completion summary

_Not completed._ Repository work done and locally verified; pending operator review, commits and the first CI run.
Notes: `harness update` re-creates `harness-wiki-publish.yml` (delete it) and reports the adapted docs workflow as a
conflict (keep it). Codex WIP is in `stash@{0}`; drop it once nothing there is wanted.
