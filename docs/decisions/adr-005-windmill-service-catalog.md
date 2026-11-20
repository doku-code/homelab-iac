---
title: 'ADR-005: Windmill over a versioned service catalog'
description: Each service declares a service.yaml catalog entry whose input schema drives a Windmill form; Windmill triggers versioned workflows and never replaces OpenTofu, Ansible or Forgejo.
published: true
tags:
- decision
- accepted
- windmill
- service-catalog
- gitops
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# ADR-005: Windmill over a versioned service catalog

> **ID:** ADR-005 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-005-windmill-service-catalog.md)

> Responsibilities update 2026-11-14 ([ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp)): Kubernetes applications are reconciled by Argo CD; Windmill triggers workflows and schedules, Headlamp administers Kubernetes, the runner executes approved jobs.

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
