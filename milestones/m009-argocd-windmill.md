---
title: M009 — Argo CD and Windmill
description: Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner.
published: true
tags:
- milestone
- active
- roadmap
editor: markdown
date: '2026-11-18T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M009 — Argo CD and Windmill

> **ID:** M009 · **Type:** milestone · **Status:** active · **Updated:** 2026-11-18 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M009-argocd-windmill.md)

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
| A change merged in Forgejo is reconciled | See [TASK-024](/tasks/task-024-argo-cd-on-k3s-and-netbox-as-its-first-application) | Done: a pushed commit reached the cluster in about three minutes; six applications `Synced` and `Healthy` | 2026-11-18 |
| Windmill on k3s | See [TASK-025](/tasks/task-025-windmill-on-k3s-reading-its-data-from-netbox) | Deployed under Argo CD; scripts from Git read NetBox | 2026-11-18 |
| A Windmill flow triggers a runner workflow | | not started | |

## Completion summary

Active. Argo CD runs and owns every service on the cluster (TASK-024), Windmill included (TASK-025).
Remaining: a Windmill flow that triggers an approved workflow on the deployment runner.
