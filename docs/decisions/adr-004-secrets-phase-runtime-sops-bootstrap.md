---
title: 'ADR-004: Secrets — Phase at runtime, SOPS + age for bootstrap'
description: Phase is the confirmed Infisical replacement (deployment gated on validating its self-hosted free edition); SOPS+age protects bootstrap material so recovery never needs Phase, Forgejo or Windmill.
published: true
tags:
- decision
- accepted
- secrets
- phase
- sops
- age
- infisical
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-004: Secrets — Phase at runtime, SOPS + age for bootstrap

> **ID:** ADR-004 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)

> Placement update 2026-11-14: Phase runs on k3s ([ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp)), on the central PostgreSQL when officially supported ([ADR-013](/docs/decisions/adr-013-central-postgresql-patroni)) and external NVMe-backed PVCs ([ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups)). Infisical stays in use until secrets migrate incrementally; the rebuild is not blocked on Phase.

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
