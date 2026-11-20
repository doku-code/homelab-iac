---
title: 'ADR-001: Rolling infrastructure rebuild'
description: Rebuild service by service using the running homelab to provision its replacement; no big-bang rebuild, no full hardware duplication.
published: true
tags:
- decision
- accepted
- migration
- strategy
editor: markdown
date: '2026-11-12T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-001: Rolling infrastructure rebuild

> **ID:** ADR-001 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-12 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-001-rolling-infrastructure-rebuild.md)

## Context

The current homelab is operational and partly configured by hand. There is not enough spare
hardware to duplicate it, and data loss or long outages are unacceptable.

## Decision

Rebuild in place, one service at a time:

1. Keep the current infrastructure running.
2. Use the existing Forgejo, runners and IaC tooling to provision the new infrastructure.
3. Deploy a clean replacement of a service, migrate its data and configuration.
4. Validate it, prepare rollback, cut over, retire the old instance after validation.
5. When an old physical machine is empty, reinstall it and join it to the new environment.
6. Repeat until the whole homelab is rebuilt and the new platform manages itself.

## Consequences

- No plan may require every machine to be available at once or all services to move together.
- Every migration carries its own data-migration, validation and rollback step (M005).
- Old and new environments coexist for a long time; ownership of each resource must stay
  unambiguous during that period ([ADR-007](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots)).
