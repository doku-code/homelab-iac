---
id: ADR-005
title: Windmill is the operations UI over a versioned service catalog
summary: Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo.
type: decision
status: accepted
importance: 5
created: 2026-11-12
updated: 2026-11-14
tags: [decision, windmill, service-catalog, gitops]
component: orchestration
related: [ARCH-platform]
related_tasks: [TASK-006]
related_milestones: [M003]
supersedes: []
superseded_by: []
---

# ADR-005: Windmill over a versioned service catalog

> Responsibilities update 2026-11-14 ([ADR-011](ADR-011-k3s-first-argocd-headlamp.md)): Kubernetes applications are reconciled by Argo CD; Windmill triggers workflows and schedules, Headlamp administers Kubernetes, the runner executes approved jobs.

## Context

The goal is to deploy services independently by filling a form, without building a custom
provisioning application. Windmill generates forms from script/flow input schemas, runs
jobs with logs and schedules, and can sync its scripts from Git.

## Decision

- Every deployable service lives in `services/<service>/` with a `service.yaml` catalog entry:
  JSON-Schema inputs, dependencies, placement, secret references (names, never values),
  DNS/route, backup and health-check declarations.
- One generic, versioned deployment entrypoint (Make target / script, wrapped by a Forgejo
  workflow) takes `service` + inputs and runs validate → `tofu plan` → approval → apply →
  Ansible → health check.
- Windmill scripts/flows are thin callers, stored in Git under `windmill/`, that build their
  form from `service.yaml` and trigger that entrypoint, then report the result.
- Windmill holds no infrastructure definitions and is never needed to recover Windmill.

## Consequences

- The catalog schema is defined early (TASK-006) so services written from M001 on fit it.
- The same deployment works from a terminal, from Forgejo Actions and from Windmill.
- Argo CD (later) consumes the same per-service definitions for Kubernetes-hosted services.
