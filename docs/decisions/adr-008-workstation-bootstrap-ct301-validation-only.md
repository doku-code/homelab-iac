---
title: 'ADR-008: Workstation bootstrap, validation-only CI'
description: The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later.
published: true
tags:
- decision
- accepted
- bootstrap
- ci
- runner
- security
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-008: Workstation bootstrap, validation-only CI

> **ID:** ADR-008 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-008-workstation-bootstrap-ct301-validation-only.md)

> Amended on 2026-11-14 by [ADR-014](/docs/decisions/adr-014-dedicated-forgejo-deployment-runner): a dedicated runner VM will execute approved workflows; bootstrap and recovery stay workstation-runnable and CT301 stays validation-only.

## Context

The briefing asked the existing CI runners to provision `pve-management`. Today the only runner,
CT301, runs validation only behind an activation gate, exposes a rootful Podman socket and has an
unresolved trust review. Infrastructure state is local to the operator workstation.

## Decision

1. The first OpenTofu apply runs from the operator workstation through the `mgmt-*` Make targets
   (saved plan, explicit approval, exact-plan hash).
2. CT301 never receives Proxmox deployment credentials and never applies infrastructure.
3. Existing CI keeps offline validation and tests (no credentials, mocked providers).
4. A dedicated, trusted infrastructure runner may be introduced later inside the management
   environment, with its own decision; no runner is installed in M001.
5. Workstation-based bootstrap and recovery remain possible permanently.

## Consequences

- "The old infrastructure builds the new" is satisfied by Forgejo (code), Infisical (bootstrap
  token) and the existing controller environment and Make workflows, not by CI execution.
- A shared state backend with locking is a prerequisite before any second executor applies (TASK-010).
