---
id: TASK-016
title: Headlamp on k3s with LAN-only ingress and token login
summary: Official chart 0.46.0, no cluster rights for the app, admin ServiceAccount token in Infisical dev:/headlamp, HTTPS ingress limited to 192.168.0.0/24.
type: task
status: completed
priority: high
milestone: M005
created: 2026-11-17
updated: 2026-11-17
tags: [k3s, headlamp]
depends_on: []
related: [ARCH-platform, GUIDE-handoff]
related_decisions: [ADR-011]
related_implementations: [services/headlamp, ansible/roles/k3s/templates/traefik-config.yaml.j2, Makefile]
related_tests: [tests/headlamp.py, tests/k3s-cluster.py]
tests_justification: ""
verification_commands: [make headlamp-check]
evidence: []
---

# TASK-016 — Headlamp on k3s with LAN-only ingress and token login

## Goal

M005: graphical Kubernetes administration before storage, databases and secrets arrive.

## Context

- [ADR-011](../docs/decisions/ADR-011-k3s-first-argocd-headlamp.md); operator direction 2026-11-17: Headlamp first, its
  credential in Infisical until Phase replaces it.

## Design

- Official chart `headlamp/headlamp` 0.46.0 (pinned in the Makefile), values in `services/headlamp/values.yaml`,
  deployed with Helm from the workstation (`make headlamp-deploy`) until Argo CD takes over (M009).
- Headlamp's own ServiceAccount has **no** cluster rights. Users log in with the token of the ServiceAccount
  `headlamp-admin` (cluster-admin) in `services/headlamp/access.yaml`; `make headlamp-token` copies its token to
  Infisical `dev:/headlamp` (`HEADLAMP_ADMIN_TOKEN`) without printing it.
- URL `https://headlamp.192.168.0.40.sslip.io/` (sslip.io resolves to the embedded address: no AdGuard change;
  Traefik's self-signed certificate until a certificate decision). HTTPS entrypoint only; Traefik middleware
  `admin-lan` allows 192.168.0.0/24 only. For that, the k3s role sets `externalTrafficPolicy: Local` on the
  bundled Traefik (HelmChartConfig) so the real client address is seen.

## Acceptance criteria

- [x] Reachable from the administration LAN only (the milestone said "workstation only": widened to the LAN
  so the operator's own PC can use it; non-LAN sources get 403)
- [x] Nodes, workloads, PVC/PV/StorageClasses, events and logs visible with the admin token

## Verification

```
make headlamp-check
make headlamp-deploy HEADLAMP_DEPLOY_APPROVED=yes && make headlamp-token
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/headlamp.py` | pinned chart renders; no ClusterRoleBinding for the app; HTTPS + admin-LAN ingress; token value never in Git; Traefik keeps client addresses | `make headlamp-check` | PASS 2026-11-17 |

`headlamp-check` needs `helm` and the chart download, so it is a workstation check, not part of CT301's CI.

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Traefik client addresses | `externalTrafficPolicy: Local` after `k3s-cluster-configure` (changed=1) | `kubectl -n kube-system get svc traefik` | 2026-11-17 |
| Deploy | Deployment rolled out, pod Running, ingress on 192.168.0.40 | `make headlamp-deploy` | 2026-11-17 |
| Network restriction | Workstation (LAN): 200; from a pod (10.42.x, not LAN): 403; plain HTTP: 404 | `curl` | 2026-11-17 |
| Login and visibility | With the token from Infisical, through Headlamp: nodes 1, pods 8, StorageClasses 1, PVs 0, events 150, pod log line; without token: 401. Browser login not clicked through by the agent | `curl` with bearer token against `/clusters/main/...` | 2026-11-17 |

## Completion summary

Completed 2026-11-17. Headlamp runs at `https://headlamp.192.168.0.40.sslip.io/` for the LAN; log in with
`HEADLAMP_ADMIN_TOKEN` from Infisical `dev:/headlamp` (moves to Phase with M008). Open: a trusted certificate
and a proper DNS name once DNS/certificates are decided.
