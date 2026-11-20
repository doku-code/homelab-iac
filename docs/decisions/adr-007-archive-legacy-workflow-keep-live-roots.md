---
title: 'ADR-007: Archive the legacy workflow, keep live roots'
description: Old AGENTS.md, roadmap, tasks and docs moved verbatim to docs/archive/codex-2026; legacy Terraform/Ansible code that still manages live resources stays at its path.
published: true
tags:
- decision
- accepted
- legacy
- archive
- state
editor: markdown
date: '2026-11-12T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-007: Archive the legacy workflow, keep live roots

> **ID:** ADR-007 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-12 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)

## Context

The repository was built by an earlier agent workflow (737-line `AGENTS.md`, French task
system, K3s/Flux-first roadmap, 27 status-heavy documents). The project direction changed
([ADR-001](/docs/decisions/adr-001-rolling-infrastructure-rebuild)). At the same time, nine legacy roots
under `terraform/stacks/` still hold the **only** state of live resources as untracked local
files beside the code.

## Decision

- The legacy documentation, roadmap, tasks and agent instructions are moved unchanged to
  `docs/archive/codex-2026/` (excluded from the knowledge map). They are evidence, not instructions.
- Legacy code (`terraform/stacks/*`, `ansible/`, `services/`, `gitops/`, `scripts/`, `tests/`,
  `Makefile`) stays at its current path while it manages live resources. Moving a root would
  separate it from its local state.
- Each legacy component is migrated, re-homed into the target layout, or retired explicitly
  in a task; nothing is deleted on the basis of being "legacy".

## Consequences

- New work goes into the target layout ([ARCH-platform](/docs/architecture/platform)); legacy
  paths shrink as services migrate.
- Backing up the legacy local state files is an early priority (TASK-010).
