---
id: ADR-017
title: Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency
summary: Authentik on k3s signs people in to the web interfaces; applications and groups are blueprints in Git, people live in Authentik, and each service keeps a local administrator.
type: decision
status: accepted
importance: 4
created: 2026-11-18
updated: 2026-11-18
tags: [decision, authentik, sso, authentication]
component: identity
topics: [authentik, single-sign-on, oidc, blueprints, break-glass]
related: [ARCH-platform, ADR-004, ADR-011, ADR-015, ADR-016]
related_tasks: [TASK-026]
related_milestones: [M014]
supersedes: []
superseded_by: []
---

# ADR-017: Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency

## Context

Every web interface of the platform had its own administrator account and password: Argo CD, Grafana,
NetBox, Windmill, Phase, Headlamp (a pasted token), four Proxmox hosts, Forgejo. The operator asked
(2026-11-18) to sign in to all of them, and to future services, through Authentik. The architecture already
named Authentik as the identity layer and required that it stays out of the bootstrap path.

## Decision

**Where it runs.** Authentik 2026.8 on k3s, official chart (pinned in
`services/argocd/apps/authentik.yaml`), one server and one worker, kept in sync by Argo CD. Database,
sessions and task queue in the shared PostgreSQL (ADR-015); this version needs no Redis. No bundled
database, no GeoIP, no update check or usage report. Authentik gets no Kubernetes credentials: it deploys
no outposts. Reachable at `https://auth.doku-lab.net` from the LAN and from the pod network (applications
exchange tokens with it from their pods).

**What is in Git, what is in Authentik.**

| Data | Authority |
|------|-----------|
| Applications, their OIDC clients, redirect addresses, which group opens what | Git: one blueprint per application in `services/authentik/blueprints/` |
| Groups that carry rights (`homelab-admins`) | Git (`homelab-access.yaml`) |
| People: accounts, passwords, passkeys and second factors, group memberships | Authentik (its web interface) |
| Client secrets, Authentik's own keys, the first administrator's password and API token | Phase, path `/authentik` (ADR-004) |

A change made by hand in Authentik to something a blueprint declares is overwritten when the blueprint is
applied again. The one account Git knows is `akadmin`, created at the first start with the password of the
secret store.

**How an application is connected**, in order of preference:

1. **OIDC in the application itself** when it supports it: the application knows who signed in and derives
   rights from the `groups` claim. Used for Argo CD, Grafana, NetBox and Windmill.
2. **Forward authentication at Traefik** (Authentik's embedded outpost) for interfaces without a login of
   their own. Not used yet.
3. **Nothing**, for addresses that machines call (log ingestion, APIs with tokens, Git over HTTPS).

**Rights.** Members of `homelab-admins` are administrators in every connected application; each
application is bound to that group in Authentik, so an account outside it is refused before it reaches the
application. Further groups are added in `homelab-access.yaml` when a second kind of user exists.

**Never a bootstrap dependency.** Every application keeps its local administrator, whose password is in
Phase, and its login form. `scripts/secrets.py`, `kubectl`, SSH, OpenTofu, Ansible and Argo CD's access to
Forgejo use their own credentials and never pass through Authentik. When Authentik is down, people sign in
with the local accounts and nothing else changes. Each application starts without its single sign-on
secret.

**Adding a service** (this is part of deploying it, not a later step): a blueprint
`homelab-<name>.yaml`, its name in `AUTHENTIK_CLIENTS` (Makefile), the application's own settings, its
entry in `tests/authentik.py` (`clients()`) and in `scripts/sso-check.py`. `make authentik-check` fails
while the two sides disagree.

## Alternatives considered

- **Keycloak, Authelia, Zitadel, Pocket ID.** Authelia and Pocket ID are lighter but offer less (no
  blueprints or equivalent for Authelia's clients beyond one file, passkeys only for Pocket ID); Keycloak
  is heavier to run and to declare. Authentik was already the project's named choice and covers OIDC,
  forward authentication, LDAP and passkeys with configuration as files.
- **Authentik outside k3s, on its own VM.** It would survive a cluster outage, but every application it
  serves is on the cluster, and nothing needs it to rebuild. Rejected; ADR-011 puts applications on k3s.
- **Configuring Authentik in its web interface, or with the OpenTofu provider.** By hand is not
  reproducible. The provider would add a root with state and make Authentik's API a dependency of a plan;
  blueprints are applied by Authentik itself from files Argo CD delivers.
- **Forward authentication in front of everything.** One mechanism, but applications would not know who
  signed in, people would log in twice, and API clients would break. Kept for interfaces without a login.
- **Argo CD's bundled Dex** (what Authentik's own guide now shows). A second broker between two components
  that speak OIDC directly. Rejected.
- **Removing the local administrators.** One login less to protect, but a failure of Authentik, of its
  database or of a blueprint would lock the operator out of the tools needed to repair it. Rejected.

## Consequences

- One account, one password and one second factor open the platform's interfaces; that account is as
  sensitive as all of them together. The operator should give it a passkey or a TOTP code.
- Losing Authentik costs convenience, not access. Its data (people, sessions) is in the shared PostgreSQL
  and is covered by whatever backs that up (M012); applications and clients are rebuilt from Git and Phase.
- Authentik's default e-mail claim says "not verified" (since 2025.10). Applications that insist on a
  verified address (Phase, Kubernetes with the e-mail as user name) need a mapping that asserts it, which is
  acceptable only while the operator creates every account.
- Windmill's free edition cannot read groups and allows ten single sign-on accounts: its administrators are
  listed by e-mail address (`WINDMILL_SSO_ADMINS`).
- Not connected yet, each needing a change outside the cluster's applications: Headlamp (the Kubernetes API
  servers must trust Authentik: a k3s setting and a restart of each server), the Proxmox hosts (an OpenID
  realm in the cluster configuration), Forgejo (an authentication source created by its administrator),
  Phase (the operator links the existing account once).
