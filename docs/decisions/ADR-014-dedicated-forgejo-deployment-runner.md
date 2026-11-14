---
id: ADR-014
title: "A dedicated Forgejo runner VM executes approved infrastructure workflows"
summary: "A runner VM created with OpenTofu and configured with Ansible runs approved OpenTofu, Ansible, k3s and Helm jobs with scoped credentials; CT301 stays validation-only. Amends ADR-008."
type: decision
status: accepted
importance: 5
created: 2026-11-14
updated: 2026-11-14
tags: [decision, forgejo, runner, ci, deployment]
component: execution
topics: [forgejo, runner, ci, opentofu, ansible, helm]
related: [ARCH-platform, ADR-008, ADR-011]
related_tasks: []
related_milestones: [M003]
supersedes: []
superseded_by: []
---

# ADR-014: Dedicated Forgejo deployment runner

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
