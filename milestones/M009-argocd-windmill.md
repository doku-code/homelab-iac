---
id: M009
title: "Argo CD and Windmill"
summary: "Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner."
type: milestone
status: active
priority: medium
created: 2026-11-12
updated: 2026-11-18
tags: [roadmap]
related_tasks: [TASK-024]
related_decisions: [ADR-011, ADR-005, ADR-014]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M005, M008]
completion_criteria: []
---

# M009 — Argo CD and Windmill

## Objective

Move Kubernetes deployments to GitOps and add workflow automation on top of the existing IaC.

**Completion criterion:** Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner.

## Scope

In scope:

- Argo CD with Forgejo as source; platform apps moved under it where appropriate
- Windmill on k3s (central PostgreSQL), calling versioned workflows

Out of scope:

- Provisioning logic inside Windmill

## Expected deliverables

- Argo CD application definitions; Windmill deployment and first flow

## Dependencies

- M005
- M008

## Acceptance criteria

- [x] A change merged in Forgejo is reconciled by Argo CD
- [ ] A Windmill flow triggers an approved runner workflow

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| A change merged in Forgejo is reconciled | See [TASK-024](../tasks/TASK-024-argo-cd-on-k3s-and-netbox-as-its-first-application.md) | Done for NetBox: a pushed commit reached the cluster in about three minutes | 2026-11-18 |
| A Windmill flow triggers a runner workflow | | not started | |

## Completion summary

Active. Argo CD runs and owns NetBox (TASK-024). Remaining: the other services under Argo CD one at a
time (Headlamp, cert-manager, observability, Phase), then Windmill on k3s and its first flow.
