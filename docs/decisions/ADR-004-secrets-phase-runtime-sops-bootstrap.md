---
id: ADR-004
title: Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets
summary: Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill.
type: decision
status: accepted
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [decision, secrets, phase, sops, age, infisical]
component: secrets
related: [ARCH-platform]
related_tasks: [TASK-011]
related_milestones: [M001, M002]
supersedes: []
superseded_by: []
---

# ADR-004: Secrets — Phase at runtime, SOPS + age for bootstrap

## Context

Infisical is the current runtime store. The rebuild needs centralised secrets, machine
identities, API/CLI integration, access isolation, Authentik SSO, CI/automation integration
and reliable backup/recovery. Dynamic database credentials and automatic rotation are not
objectives. The platform must stay recoverable when the secrets service itself is down.

## Decision

- **Runtime:** Phase (self-hosted) is the confirmed replacement for Infisical (operator decision,
  2026-11-12). Its deployment in M002 is gated on validating the self-hosted free edition:
  service identities, API/CLI, access controls, Authentik SSO and backup/restore.
- **Bootstrap/recovery:** SOPS + age encrypts the small set of credentials needed before
  Phase/Forgejo exist (Proxmox API token, initial SSH keys, Phase recovery material).
  Encrypted files may be committed; age private keys are kept outside the infrastructure they protect.
- **Transition:** Infisical stays operational until Phase is deployed, backed up, tested and
  its consumers are migrated. No automatic fallback between stores.

## Consequences

- Each consumer declares which store it uses; migration happens consumer by consumer.
- Recovery documentation must cover age key custody (operator-held, off-site).
