---
id: TASK-024
title: Argo CD on k3s and NetBox as its first application
summary: Install Argo CD from the workstation, restrict it to this repository and named namespaces, and move NetBox under it without a restart.
type: task
status: completed
priority: medium
milestone: M009
created: 2026-11-18
updated: 2026-11-18
tags: [argocd, gitops]
depends_on: [TASK-023, TASK-022]
related: [ARCH-platform]
related_decisions: [ADR-011, ADR-016]
related_implementations:
  - services/argocd/values.yaml
  - services/argocd/access.yaml
  - services/argocd/apps/netbox.yaml
  - Makefile
related_tests:
  - tests/argocd.py
  - tests/netbox.py
tests_justification: ""
verification_commands:
  - make argocd-check
  - make netbox-check
evidence: []
---

# TASK-024 — Argo CD on k3s and NetBox as its first application

## Goal

Argo CD runs on the cluster and keeps one real application in sync with the main branch on Forgejo, with
a pattern the other services can follow one at a time.

## Context

- [ADR-011](../docs/decisions/ADR-011-k3s-first-argocd-headlamp.md): Argo CD reconciles applications from
  Forgejo. Until now every service on k3s was installed by a Make target from the workstation.
- The operator confirmed on 2026-11-18 that Argo CD should manage the cluster's services.

## Design

- `services/argocd/values.yaml`: chart `argo/argo-cd` 10.18.1 (Argo CD 3.6.1), one replica per component,
  no Dex, no notifications, ApplicationSet controller scaled to zero, TLS ended at Traefik.
- `services/argocd/access.yaml`: route `argocd.doku-lab.net` (LAN only) and the project `platform`:
  sources are this repository on Forgejo and the declared chart registries, destinations are named
  namespaces of this cluster, the only cluster-wide kind is `Namespace`.
- `services/argocd/apps/<name>.yaml`: one Application per service: the pinned chart, the values file from
  this repository, and the service's own manifests. Automatic sync with self-heal, **no automatic pruning**.
- Argo CD itself is installed by `make argocd-deploy` (it cannot deploy itself on a rebuilt cluster).
  Secrets stay out of Git: a service's Make target writes its Secret from the secret store, then applies
  the Application (`make netbox-deploy`).
- The repository on Forgejo is readable without credentials on the LAN, so Argo CD holds no Git credential.

## Acceptance criteria

- [x] Argo CD deployed from the repository, LAN only, admin password in the secret store
- [x] Applications limited to this repository, this cluster and named namespaces
- [x] NetBox moved under Argo CD without a restart; Helm no longer tracks it
- [x] A change merged on main reaches the cluster without anyone running a command
- [ ] The other services (Headlamp, cert-manager, observability, Phase) moved under Argo CD

## Verification

```
make argocd-check
make argocd-deploy ARGOCD_DEPLOY_APPROVED=yes
kubectl --context doku-lab -n argocd get applications
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/argocd.py` | Rendered chart (pinned images, single replicas, no Dex or notifications, insecure server only behind Traefik, repository entries without credentials), route, project limits, every Application (project, pinned chart, values file exists, no Secret in the applied files, no pruning), Make guards | `make argocd-check` | PASS 2026-11-18 |
| `tests/netbox.py` | The chart version comes from the Application; `netbox-deploy` no longer runs Helm | `make netbox-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Deployment | Release `argocd` installed; controller, server, repo server and Redis Running (about 290 MiB together); `https://argocd.doku-lab.net/` 200 after a few seconds (404 at first, while Traefik loaded the route) | `.local/argocd-deploy-1.log`, `kubectl -n argocd get pods` | 2026-11-18 |
| Admin password | Moved from `argocd-initial-admin-secret` to the secret store (`/argocd`), the Kubernetes Secret deleted; login with the stored password returns a session | `make argocd-password`, `/api/v1/session` | 2026-11-18 |
| Preview before adoption | Application registered without automatic sync: 13 objects `OutOfSync` only for lack of Argo CD's tracking mark; `kubectl diff` of the rendered chart and manifests against the cluster showed one difference, the chart's test pod, which Argo CD ignores | `kubectl diff` | 2026-11-18 |
| Adoption | Automatic sync enabled: `Synced`, `Healthy`; the three NetBox pods kept their names (no restart); login page 200 | `make netbox-deploy`, `kubectl get application netbox` | 2026-11-18 |
| One owner | Helm's two release records for `netbox` deleted; `helm list -n netbox` is empty | `kubectl -n netbox get secret -l owner=helm` | 2026-11-18 |
| Change through Git | Commit `c20c904` (a label on the Valkey Service) pushed at 15:49:42; the label was on the cluster object at 15:53:01 without any command; application `Synced` at that revision | `kubectl get svc netbox-valkey` | 2026-11-18 |

## Completion summary

Completed 2026-11-18 for its scope: Argo CD runs and owns NetBox.

Remaining for M009 (not in this task): move the other services under Argo CD one at a time, each with a
preview like the one above. Phase needs care: its deployment patches the frontend after the chart
(`services/phase/frontend-password-policy.yaml`), which Argo CD would revert unless the patch becomes part
of what it renders. cert-manager and the observability charts need cluster-wide kinds added to the project.
Then Windmill. Argo CD depends on Forgejo being reachable (`git.doku-lab.net`, served by the legacy Caddy and
TrueNAS) to pick up changes; the cluster keeps running without it.
