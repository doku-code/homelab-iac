---
id: ADR-004
title: Phase for runtime secrets, SOPS + age for bootstrap and recovery secrets
summary: Phase is the intended Infisical replacement (pending capability and licence validation); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill.
type: decision
status: proposed
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

- **Runtime:** Phase (self-hosted) is the selected replacement for Infisical. Status stays
  `proposed` until its self-hosted capabilities and licensing (SSO, service accounts, backups)
  are verified in M002.
- **Bootstrap/recovery:** SOPS + age encrypts the small set of credentials needed before
  Phase/Forgejo exist (Proxmox API token, initial SSH keys, Phase recovery material).
  Encrypted files may be committed; age private keys are kept outside the infrastructure they protect.
- **Transition:** Infisical stays operational until Phase is deployed, backed up, tested and
  its consumers are migrated. No automatic fallback between stores.

## Consequences

- Each consumer declares which store it uses; migration happens consumer by consumer.
- Recovery documentation must cover age key custody (operator-held, off-site).
