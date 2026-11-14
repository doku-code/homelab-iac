---
id: ADR-008
title: Bootstrap runs from the operator workstation; CT301 stays validation-only
summary: The first OpenTofu applies on pve-management run from the workstation through approval-gated Make targets; CT301 never holds Proxmox credentials nor applies; a trusted runner comes later.
type: decision
status: accepted
importance: 5
created: 2026-11-12
updated: 2026-11-14
tags: [decision, bootstrap, ci, runner, security]
component: execution
related: [ARCH-platform, INV-pve-management-bootstrap]
related_tasks: [TASK-006, TASK-008]
related_milestones: [M001]
supersedes: []
superseded_by: []
---

# ADR-008: Workstation bootstrap, validation-only CI

> Amended on 2026-11-14 by [ADR-014](ADR-014-dedicated-forgejo-deployment-runner.md): a dedicated runner VM will execute approved workflows; bootstrap and recovery stay workstation-runnable and CT301 stays validation-only.

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
