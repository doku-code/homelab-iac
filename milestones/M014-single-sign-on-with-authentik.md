---
id: M014
title: Single sign-on with Authentik
summary: Authentik runs on k3s and signs the operator in to the web interfaces of the platform; each new service is added to it in the same change, and every service keeps a local administrator.
type: milestone
status: active
priority: medium
created: 2026-11-18
updated: 2026-11-18
tags: [roadmap, authentik, sso]
related_tasks: [TASK-026]
related_decisions: [ADR-017, ADR-004, ADR-011]
related: [ARCH-platform, DOC-project-overview]
depends_on: [M004, M007, M009]
completion_criteria: []
---

# M014 — Single sign-on with Authentik

## Objective

One account opens every web interface of the platform, rights come from one group, and a service that is
added later is connected in the change that deploys it, without Authentik becoming something the platform
needs in order to be rebuilt or repaired.

**Completion criterion:** every web interface of the platform that can use single sign-on does, the
operator signs in with a personal account protected by a second factor, and the local administrators have
been tested with Authentik stopped.

## Scope

In scope:

- Authentik on k3s from this repository, on the shared PostgreSQL.
- Applications, clients and groups as blueprints in Git; client secrets in the secret store.
- Sign-in for Argo CD, Grafana, NetBox, Windmill, Phase, Headlamp, the Proxmox hosts and Forgejo.
- Forward authentication at Traefik for interfaces without a login of their own.

Out of scope:

- Access from outside the LAN; people other than the operator (groups are added when they exist).
- Removing local administrators; Authentik as a dependency of any deployment tool.
- LDAP, RADIUS, SCIM.

## Expected deliverables

- `services/authentik/`, `scripts/authentik-admin.py`, `scripts/sso-check.py`, `scripts/ensure-secrets.py`,
  Make targets `authentik-*` and `sso-check`.
- [ADR-017](../docs/decisions/ADR-017-authentik-is-the-single-sign-on-of-the-platform-declared-in.md).

## Dependencies

- k3s (M004), shared PostgreSQL (M007), Argo CD (M009); DNS and certificates from TASK-022.

## Acceptance criteria

- [x] Authentik deployed from the repository, LAN only, credentials in the secret store
- [x] Argo CD, Grafana, NetBox and Windmill sign in through it, administrators from one group
- [x] Every connected application still accepts its local administrator
- [ ] Headlamp signs in through it (the Kubernetes API servers trust Authentik)
- [ ] The Proxmox hosts, Forgejo and Phase sign in through it
- [ ] Forward authentication available for interfaces without a login, used by at least one
- [ ] The operator uses a personal account with a second factor
- [ ] Local administrators tested with Authentik stopped

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Deployment, four applications, local administrators | See [TASK-026](../tasks/TASK-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb.md) | Done: `make sso-check` signs in to all four as administrator; the four local logins answer | 2026-11-18 |
| Headlamp, Proxmox, Forgejo, Phase | | not started: each needs an approval or a step by the operator | |
| Forward authentication | | not started | |
| Personal account, second factor, test with Authentik stopped | | not verified | |

## Completion summary

Active. Authentik runs and four applications use it (TASK-026). Remaining: the applications that need a
change outside the cluster's applications, forward authentication, and the operator's own account.
