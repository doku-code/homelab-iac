---
id: M014
title: Single sign-on with Authentik
summary: Authentik runs on k3s and signs the operator in to the web interfaces of the platform; each new service is added to it in the same change, and every service keeps a local administrator.
type: milestone
status: active
priority: medium
created: 2026-11-18
updated: 2026-11-19
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
- [x] Forward authentication available for interfaces without a login, used by at least one
- [ ] The operator uses a personal account with a second factor
- [ ] Local administrators tested with Authentik stopped

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Deployment, four applications, local administrators | See [TASK-026](../tasks/TASK-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb.md) | Done: `make sso-check` signs in to all four as administrator; the four local logins answer | 2026-11-18 |
| Proxmox | `make proxmox-sso`, `make sso-check` | Done: realm `authentik` on the doku-lab cluster (approved by the operator 2026-11-20); `ok proxmox signed in as akadmin@authentik, groups ['homelab-admins-authentik'], 47 privileges on /`. The default realm, `root@pam` and the API tokens are unchanged | 2026-11-20 |
| Headlamp | | not started: the Kubernetes API servers must be told to trust Authentik (a k3s setting and a restart of each server); waits for the operator's approval | |
| Forgejo | | not started: Forgejo declares sign-in sources only in its administration pages or with its command line inside the container (no API), and the token on the workstation has no administration scope | |
| Phase | | not started: the operator links their own account | |
| Forward authentication | `make sso-check` (see [TASK-027](../tasks/TASK-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab.md)) | Done: the dashboard answers 302 to Authentik without a session and 200 with one; embedded outpost, no Kubernetes connection | 2026-11-19 |
| Personal account | Authentik API: groups and access check of the operator's account; `make windmill-sso` | Account exists in `homelab-admins` and `authentik Admins`, passes the access check of the four applications, declared as Windmill administrator (address kept in the secret store). It has not signed in yet and has no second factor | 2026-11-19 |
| Second factor, test with Authentik stopped | | not verified | |

## Completion summary

Active. Authentik runs and four applications use it (TASK-026). Remaining: the applications that need a
change outside the cluster's applications, forward authentication, and the operator's own account.
