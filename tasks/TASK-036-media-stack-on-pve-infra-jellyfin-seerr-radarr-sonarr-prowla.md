---
id: TASK-036
title: "Media stack on pve-infra: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on a Compose VM"
summary: "VM media-01 on pve-infra with Docker Compose: Jellyfin, Seerr, the Arr tools and qBittorrent; shared PostgreSQL, NAS read-only, a test area."
type: task
status: in-progress
priority: medium
milestone: M010
created: 2026-11-26
updated: 2026-11-26
tags: []
depends_on: []
related: []
related_decisions: []
related_implementations: []
related_tests: [tests/media.py, terraform/stacks/media/tests/media.tftest.hcl, tests/postgresql.py]
tests_justification: ""
verification_commands: ["make media-check", "make postgresql-check", "make authentik-check"]
evidence: []
---

<!--
Task: the operational unit that guides an agent through one implementation step.
Create when: work spans a session boundary or needs explicit verification evidence.
Status vocabulary: planned | in-progress | blocked | completed | cancelled.
Rules:
- Never mark completed without evidence (command output, test result, commit).
- If a command failed, record the failure. If nothing was verified, write "not verified".
- Keep summaries proportional: a small task needs two factual sentences, not a log.
- A feature or fix ships with its tests in the project's test framework, written in this task and listed in
  `related_tests`. If no test is possible, say why in `tests_justification`; `harness check` refuses a completed
  task that has implementation paths but neither.
-->

# Media stack on pve-infra: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on a Compose VM

## Goal



## Context

Relevant documents, prior decisions and existing implementations to reuse:

-

## Acceptance criteria

- [ ]

## Verification

Commands that prove the criteria (also listed in `verification_commands`):

```
```

## Tests

Tests added or updated for this change (paths also listed in `related_tests`):

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| | | | not run |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| | not verified | | |

## Completion summary

_Not completed._
