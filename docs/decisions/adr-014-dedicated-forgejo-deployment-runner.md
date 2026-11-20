---
title: 'ADR-014: Dedicated Forgejo deployment runner'
description: A runner VM created with OpenTofu and configured with Ansible runs approved OpenTofu, Ansible, k3s and Helm jobs with scoped credentials; CT301 stays validation-only. Amends ADR-008.
published: true
tags:
- decision
- accepted
- forgejo
- runner
- ci
- deployment
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# ADR-014: Dedicated Forgejo deployment runner

> **ID:** ADR-014 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-014-dedicated-forgejo-deployment-runner.md)

## Context

ADR-008 runs every apply from the operator workstation and keeps the CT301 runner validation-only.
The platform roadmap (k3s, Helm, Argo CD bootstrap) needs repeatable automated execution.

## Decision

- A dedicated runner VM, created with OpenTofu and configured with Ansible, registered with the
  existing Forgejo, executes approved workflows: OpenTofu plan/apply, Ansible, k3s provisioning, Helm
  and platform bootstrap.
- Its credentials are scoped to what those jobs need; privileged jobs run only from protected refs and
  approved triggers, never from pull requests. CT301 keeps no deployment credentials (ADR-008).
- Before the runner applies a root, that root's state must be reachable by the runner with one writer
  at a time; this is the point where a shared state backend is decided (TASK-010), not earlier.

## Consequences

- ADR-008 still governs the bootstrap and recovery path: everything the runner does stays runnable
  from a workstation.
