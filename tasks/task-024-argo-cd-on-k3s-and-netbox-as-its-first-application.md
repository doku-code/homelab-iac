---
title: TASK-024 — Argo CD on k3s and every service of the cluster under it
description: Install Argo CD, restrict it to this repository and named namespaces, and move every service of the cluster under it without a restart.
published: true
tags:
- task
- completed
- argocd
- gitops
editor: markdown
date: '2026-11-18T00:00:00.000Z'
dateCreated: '2026-11-18T00:00:00.000Z'
---

# TASK-024 — Argo CD on k3s and every service of the cluster under it

> **ID:** TASK-024 · **Type:** task · **Status:** completed · **Updated:** 2026-11-18 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-024-argo-cd-on-k3s-and-netbox-as-its-first-application.md)

## Goal

Argo CD runs on the cluster and keeps one real application in sync with the main branch on Forgejo, with
a pattern the other services can follow one at a time.

## Context

- [ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp): Argo CD reconciles applications from
  Forgejo. Until now every service on k3s was installed by a Make target from the workstation.
- The operator confirmed on 2026-11-18 that Argo CD should manage the cluster's services.

## Design

- `services/argocd/values.yaml`: chart `argo/argo-cd` 10.18.1 (Argo CD 3.6.1), one replica per component,
  no Dex, no notifications, ApplicationSet controller scaled to zero, TLS ended at Traefik.
- `services/argocd/access.yaml`: route `argocd.doku-lab.net` (LAN only) and two projects. `platform`
  (NetBox, Headlamp, monitoring, Phase): this repository and the listed chart registries, named namespaces,
  cluster-wide kinds limited to namespaces, cluster roles and chart-shipped definitions. `infrastructure`
  (certificates and routes, storage driver): may reach `kube-system` and create any cluster-wide kind.
- `services/argocd/apps/<name>.yaml`: one Application per service: the pinned chart, the values file from
  this repository, and the service's own manifests. Automatic sync with self-heal, **no automatic pruning**.
  Two services need kustomize: monitoring builds its ConfigMaps from files, and Phase renders its chart
  through kustomize so that the password-length patch is part of what Argo CD keeps in place.
- Chart versions stay in the Makefile for the offline tests; `tests/argocd.py` checks every Application
  uses the same repository and version.
- Argo CD itself is installed by `make argocd-deploy` (it cannot deploy itself on a rebuilt cluster).
  Secrets stay out of Git: a service's Make target writes its Secret from the secret store, then applies
  the Application (`make netbox-deploy`).
- The repository on Forgejo is readable without credentials on the LAN, so Argo CD holds no Git credential.

## Acceptance criteria

- [x] Argo CD deployed from the repository, LAN only, admin password in the secret store
- [x] Applications limited to this repository, this cluster and named namespaces
- [x] NetBox moved under Argo CD without a restart; Helm no longer tracks it
- [x] A change merged on main reaches the cluster without anyone running a command
- [x] The other services (Headlamp, monitoring, certificates and routes, storage driver, Phase) moved under Argo CD

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
| Previews of the five other services | Rendered as the Make targets did and compared with the cluster: no difference except one-off jobs of the charts (cert-manager start-up check, Phase migrations). Phase rendered with Argo CD's own kustomize and Helm inside its pod: 13 objects, the 10-character patch included | `kubectl diff` | 2026-11-18 |
| EndpointSlices | Argo CD 3 ignores EndpointSlices by default; the routes to services outside k3s are Services with hand-written EndpointSlices. The exclusion list is overridden without that kind; the ingress application then showed 98 objects instead of 84 | `services/argocd/values.yaml` | 2026-11-18 |
| Monitoring, first attempt | Sync refused, nothing changed: the Alloy chart ships a definition (CRD) the `platform` project did not allow. Allowed, pushed, synced | Argo CD sync error | 2026-11-18 |
| Handover of the five | `headlamp`, `storage`, `monitoring`, `ingress`, `phase`: `Synced`, `Healthy`; in every namespace the pods kept their names and restart counts; Helm's release records removed (Helm now lists only `argocd` and the k3s-managed Traefik) | `.local/argocd-handover-*.log` | 2026-11-18 |
| After the handover | Wildcard certificate Ready; `phase`, `grafana`, `headlamp`, `netbox`, `argocd`, `wiki`, `vault`, `home`, `pve-core`, `truenas` answer; the secret store returns values; the frontend still carries the 10-character rule; Argo CD uses about 490 MiB | `curl`, `scripts/secrets.py run` | 2026-11-18 |

## Completion summary

Completed 2026-11-18. Argo CD runs and owns every service on the cluster except itself (installed by
`make argocd-deploy`) and Traefik (managed by k3s). A service is changed by a commit on `main`; its Make
target only writes the Secrets that are not in Git and registers the Application.

Known limits: Argo CD needs Forgejo (`git.doku-lab.net`, served by the legacy Caddy and TrueNAS) and the
chart registries to pick up changes; the cluster keeps running without them. The Phase pods read their
settings only at start, so a change of host or settings needs a manual `rollout restart`. Each sync of
Phase runs its migration job once. Nothing is pruned automatically: an object removed from Git stays until
a person deletes it. Rebuilding the cluster from nothing through Argo CD has not been exercised.

Remaining for M009: Windmill on k3s and its first flow.
