---
title: 'ADR-006: Compose first, Kubernetes later'
description: Applications run as Compose projects on VMs; k3s with Argo CD is a future option. Supersedes the legacy K3s/Flux-first direction.
published: true
tags:
- decision
- superseded
- compose
- kubernetes
- k3s
- argocd
- flux
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-006: Compose first, Kubernetes later

> **ID:** ADR-006 · **Type:** decision · **Status:** superseded · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-006-compose-first-kubernetes-later.md)

> Superseded on 2026-11-14 by [ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp): k3s is the application platform from the start.

## Context

The legacy repository started a K3s + Flux "Stage A" lab (three server VMs on `pve-lab`) with
a demo app and Homepage. For the services in scope, Kubernetes adds operational cost without
a demonstrated need yet.

## Decision

- Applications are deployed as Docker Compose projects on dedicated VMs (or LXCs where justified).
- k3s with Argo CD is a later milestone (M008) for workloads that benefit from it; Flux is not
  the target GitOps controller.
- The legacy Stage A K3s/Flux code stays in place as legacy until its guests are retired
  ([ADR-007](/docs/decisions/adr-007-archive-legacy-workflow-keep-live-roots)).

## Consequences

- No distributed storage or HA cluster work on the critical path.
- Service definitions stay portable so a later move to Kubernetes does not require rewriting them.
