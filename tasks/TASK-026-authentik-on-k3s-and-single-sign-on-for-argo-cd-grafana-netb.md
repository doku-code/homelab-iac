---
id: TASK-026
title: Authentik on k3s and single sign-on for Argo CD, Grafana, NetBox and Windmill
summary: Authentik 2026.8.5 under Argo CD on the shared PostgreSQL; applications and groups as blueprints; OIDC sign-in wired for Argo CD, Grafana, NetBox and Windmill with local administrators kept.
type: task
status: completed
priority: medium
milestone: M014
created: 2026-11-18
updated: 2026-11-18
tags: [authentik, sso, argocd, grafana, netbox, windmill]
depends_on: [TASK-024, TASK-018]
related: [ARCH-platform]
related_decisions: [ADR-017, ADR-004, ADR-011, ADR-015]
related_implementations:
  - services/authentik/values.yaml
  - services/authentik/access.yaml
  - services/authentik/kustomization.yaml
  - services/authentik/blueprints/
  - services/argocd/apps/authentik.yaml
  - services/argocd/values.yaml
  - services/observability/grafana.yaml
  - services/netbox/values.yaml
  - services/netbox/access.yaml
  - scripts/authentik-admin.py
  - scripts/ensure-secrets.py
  - scripts/sso-check.py
  - scripts/windmill-admin.py
related_tests:
  - tests/authentik.py
  - tests/netbox.py
  - tests/argocd.py
tests_justification: ""
verification_commands:
  - make authentik-check
  - make netbox-check
  - make argocd-check
evidence: []
---

# TASK-026 — Authentik on k3s and single sign-on for Argo CD, Grafana, NetBox and Windmill

## Goal

The operator signs in once, at Authentik, and reaches Argo CD, Grafana, NetBox and Windmill as an
administrator; every one of them still accepts its local administrator when Authentik is down.

## Context

- Operator request 2026-11-18: use Authentik to sign in to the services, current and future.
- [ADR-017](../docs/decisions/ADR-017-authentik-is-the-single-sign-on-of-the-platform-declared-in.md): what is
  in Git, what is in Authentik, how an application is connected, why local administrators stay.
- No Authentik existed in the old environment: this is a new installation, nothing to migrate.

## Design

- **Authentik**: chart `authentik` 2026.8.5 under Argo CD, one server, one worker, database `authentik` on
  the shared PostgreSQL over TLS, no Redis, no Kubernetes credentials, route `auth.doku-lab.net` for the LAN
  and the pod network.
- **Blueprints** (`services/authentik/blueprints/`, delivered as one ConfigMap): the group `homelab-admins`
  with `akadmin` in it, and per application an OIDC client, the application and its binding to the group.
  Client secrets are read from the worker's environment.
- **Secrets**: `scripts/ensure-secrets.py` creates what the store lacks and never replaces a value;
  `make authentik-deploy` writes them into the Secret `authentik-secrets`; each application's deploy target
  writes its own client secret (`argocd-sso`, `grafana-sso`, `netbox-sso`), Windmill gets it through its API.
- **Applications**: Argo CD (`oidc.config`, `g, homelab-admins, role:admin`, no default role), Grafana
  (generic OAuth, `GrafanaAdmin` for the group, nobody else gets a role), NetBox (python-social-auth with one
  added step that sets the superuser flag from the group), Windmill (instance setting `oauths`; its free
  edition cannot read groups, so administrators are listed by address in `WINDMILL_SSO_ADMINS`).
- **Proof**: `scripts/sso-check.py` signs in to each application through Authentik as a browser would and
  asks the application who it sees.

## Acceptance criteria

- [x] Authentik deployed from the repository through Argo CD, LAN only, no default or printed credentials
- [x] Applications, clients and the administrators' group declared in Git and applied by Authentik
- [x] Sign-in through Authentik works for Argo CD, Grafana, NetBox and Windmill with administrator rights
- [x] An account outside `homelab-admins` is refused for each application
- [x] Every local administrator still signs in
- [ ] Headlamp, the Proxmox hosts, Forgejo and Phase connected (each needs a step outside this task, see below)

## Verification

```
make authentik-check
scripts/secrets.py run /authentik /postgresql -- make authentik-deploy AUTHENTIK_DEPLOY_APPROVED=yes
scripts/secrets.py run /authentik -- make authentik-status
scripts/secrets.py run /authentik -- make sso-check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/authentik.py` | Rendered chart (pinned image, single replicas, no service account token, no secret among plain values, database over TLS), route, blueprints (secret only from the environment, grant types, exact redirect addresses, group binding, nothing deleted), both sides of each client, `ensure-secrets` never replacing a value, the tools' write calls | `make authentik-check` | PASS 2026-11-18 |
| `tests/netbox.py` | The added sign-in step: superuser exactly while the group is in the claim, nothing written when unchanged; its mount | `make netbox-check` | PASS 2026-11-18 |
| `tests/argocd.py` | Eight applications, chart pin of Authentik, project allows its repository and namespace | `make argocd-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database and name | Database and role `authentik` created on the three PostgreSQL members; `auth.doku-lab.net` answers 192.168.0.40 | `.local/postgresql-configure-authentik.log`, `.local/dns-configure-auth.log`, `dig` | 2026-11-18 |
| Deployment | Application `authentik` `Synced` and `Healthy`, two pods Running (the image pull took four minutes on one node), `/-/health/ready/` 200 | `.local/authentik-deploy.log` | 2026-11-18 |
| Blueprints | Five `successful`; four applications each `open to: homelab-admins`; `akadmin` in `authentik Admins` and `homelab-admins`; tokens signed RS256; no Kubernetes connection, embedded outpost without providers | `make authentik-status`, API | 2026-11-18 |
| First sign-in attempts | Refused by Authentik: `Invalid grant_type for provider`. Since 2026.5 a provider allows no grant unless listed; `grant_types` added to the blueprints | Authentik server log, commit `fix(authentik): list the grant types…` | 2026-11-18 |
| Sign-in end to end | `argocd`: groups include `homelab-admins`, sees 8 applications. `grafana`: `akadmin`, server administrator. `netbox`: reads accounts and API tokens with no assigned permission (superuser). `windmill`: administrator, workspace `homelab` | `make sso-check` | 2026-11-18 |
| Windmill account type | A pre-created account of type `pending_oauth` was refused at sign-in; accounts are now created with the type `authentik` | `scripts/windmill-admin.py sso` | 2026-11-18 |
| Refusal | Authentik's access check for an account outside the group (its own outpost service account): refused for all four applications | `GET /core/applications/<slug>/check_access/` | 2026-11-18 |
| Local administrators | Argo CD 200, Grafana 200, NetBox 201 (a token valid until midnight was created by this check), Windmill 200 | each application's login API | 2026-11-18 |

## Completion summary

Completed 2026-11-18 for its scope. Authentik runs at `https://auth.doku-lab.net` (user `akadmin`, password
`AUTHENTIK_BOOTSTRAP_PASSWORD` at `/authentik` in the secret store) and signs its administrators in to Argo
CD, Grafana, NetBox and Windmill.

Not done, each waiting for a decision or a step that is the operator's:

- **Headlamp**: the three Kubernetes API servers must trust Authentik (a k3s setting and a restart of each
  server, one at a time). Cluster-wide change, not applied without approval.
- **Proxmox hosts**: an OpenID realm in the cluster configuration. Not applied without approval.
- **Forgejo**: an authentication source, created by its administrator (no administrator credential in the
  store).
- **Phase**: its free edition supports Authentik; an existing password account must be linked by its owner
  (Account, sign-in methods), and Phase needs an e-mail claim marked verified.
- The operator's personal account in Authentik, a passkey or TOTP code for it, and whether `akadmin` stays in
  daily use.
- Not tested: an expired session, sign-out from one application ending the others, Authentik being down
  (the local accounts were tested while it was up).
