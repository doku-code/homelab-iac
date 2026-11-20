---
title: TASK-001 — Reset repository to the agent harness and record the rebuild direction
description: Install the agent harness, archive the legacy Codex workflow, and document vision, architecture, decisions and roadmap.
published: true
tags:
- task
- in-progress
- harness
- repository
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# TASK-001 — Reset repository to the agent harness and record the rebuild direction

> **ID:** TASK-001 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-001-repository-reset-and-alignment.md)

**Authorization:** OFFLINE_CODE (repository only). A task status never authorizes a live change by itself.

## Goal

Make the repository a clean, harness-managed starting point whose docs carry the agreed rebuild direction.

## Context

- Project briefing (2026-11-12) and [ARCH-platform](/docs/architecture/platform)
- Legacy workflow archived in [docs/archive/codex-2026](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/archive/codex-2026/AGENTS.md) ([ADR-007](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots))
- Uncommitted Codex WIP (Windmill + VM208 infra runner) stashed as `stash@{0}`, not committed

## Acceptance criteria

- [ ] Harness installed (skills, agents, settings, managed blocks) and pinned in requirements-agents.txt
- [ ] CI docs validation follows the main-only activation gate; wiki publication (operator decision 2026-11-17,
  replacing "no wiki publication") uses the same gate, the `homelab-iac` runner and only the job token
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
| Wiki publication + CI on 8c03161 | PASS: Documentation validation run 81, Wiki publication run 82 (job token initialised the wiki: 53 pages with Home from README and generated _Sidebar), validate run 83 | Forgejo Actions runs 81–83, wiki API | 2026-11-17 |
| `validate.yml` on f501ff1 | FAIL run 51 after 6 s; cause unknown, log not yet read | Forgejo Actions run 51 | 2026-11-12 |

## Completion summary

_Not completed._ Repository work done and locally verified; pending operator review, commits and the first CI run.
Notes: `harness update` reports the adapted docs and wiki workflows as conflicts (keep both adaptations). Codex WIP is in `stash@{0}`; drop it once nothing there is wanted.
