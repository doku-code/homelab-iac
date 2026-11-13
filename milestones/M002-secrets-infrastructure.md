---
id: M002
title: "Secrets infrastructure (Phase)"
summary: "Phase deployed, recoverable independently, and used by deployment automation; controlled migration from Infisical begins."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-12
tags: [secrets, phase]
related_tasks: []
related_decisions: [ADR-004]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M002 — Secrets infrastructure (Phase)

## Objective

Establish the new secrets management foundation.

**Completion criterion:** Phase deployed, recoverable independently, and used by deployment automation; controlled migration from Infisical begins.

## Scope

In scope:

- Validate Phase self-hosted capabilities and licensing
- Deploy Phase in an isolated, persistent environment
- Authentication, Authentik SSO where appropriate, service-account identities
- Backup and recovery
- Forgejo/Ansible integration
- Consumer-by-consumer migration from Infisical

Out of scope:

- Dynamic database credentials, automatic rotation

## Expected deliverables

- Phase service definition in services/phase
- Machine identities per consumer
- Backup/restore evidence

## Dependencies

- M001

## Acceptance criteria

- [ ] Deployment automation retrieves secrets from Phase with a scoped identity
- [ ] Phase restored from backup without Phase itself
- [ ] Infisical still serves unmigrated consumers

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
