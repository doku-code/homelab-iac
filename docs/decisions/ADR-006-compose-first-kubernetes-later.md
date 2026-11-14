---
id: ADR-006
title: Docker Compose first; k3s and Argo CD later, only where they add value
summary: Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction.
type: decision
status: superseded
importance: 4
created: 2026-11-12
updated: 2026-11-14
tags: [decision, compose, kubernetes, k3s, argocd, flux]
component: application
related: [ARCH-platform]
related_tasks: []
related_milestones: [M005, M008]
supersedes: []
superseded_by: [ADR-011]
---

# ADR-006: Compose first, Kubernetes later

> Superseded on 2026-11-14 by [ADR-011](ADR-011-k3s-first-argocd-headlamp.md): k3s is the application platform from the start.

## Context

The legacy repository started a K3s + Flux "Stage A" lab (three server VMs on `pve-lab`) with
a demo app and Homepage. For the services in scope, Kubernetes adds operational cost without
a demonstrated need yet.

## Decision

- Applications are deployed as Docker Compose projects on dedicated VMs (or LXCs where justified).
- k3s with Argo CD is a later milestone (M008) for workloads that benefit from it; Flux is not
  the target GitOps controller.
- The legacy Stage A K3s/Flux code stays in place as legacy until its guests are retired
  ([ADR-007](ADR-007-archive-legacy-workflow-keep-live-roots.md)).

## Consequences

- No distributed storage or HA cluster work on the critical path.
- Service definitions stay portable so a later move to Kubernetes does not require rewriting them.
