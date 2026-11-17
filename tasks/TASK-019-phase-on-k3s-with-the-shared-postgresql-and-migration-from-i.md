---
id: TASK-019
title: Phase on k3s with the shared PostgreSQL and migration from Infisical
summary: Phase Console v2.79.0 runs on k3s with its database on the shared PostgreSQL; scripts/secrets.py selects the store, migrates and verifies; cutover waits for the operator's Phase account.
type: task
status: in-progress
priority: high
milestone: M008
created: 2026-11-17
updated: 2026-11-17
tags: [phase, secrets, infisical, k3s, migration]
depends_on: [TASK-018]
related: [ARCH-platform, GUIDE-handoff]
related_decisions: [ADR-004, ADR-015, ADR-011]
related_implementations: [services/phase, scripts/secrets.py, ansible/vars/postgresql-apps.yml, ansible/roles/admin_workstation/defaults/main.yml, Makefile]
related_tests: [tests/phase.py, tests/secrets.py]
tests_justification: ""
verification_commands: [make phase-check]
evidence: []
---

# TASK-019 — Phase on k3s with the shared PostgreSQL and migration from Infisical

## Goal

M008: Phase replaces Infisical. Every key moves to Phase, the tooling reads from Phase, then Infisical is
shut down (operator direction 2026-11-17; the shutdown itself needs the operator's confirmation).

## Context

- [ADR-004](../docs/decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md): Phase at runtime, an encrypted copy
  of the bootstrap credentials outside it, no automatic fallback between stores.
- Phase runs on k3s and k3s is a single server that is rebuilt from IaC: a rebuild removes the Kubernetes
  Secret that holds Phase's own keys. The data survives (it is in PostgreSQL, outside k3s), but without
  `PHASE_SERVER_SECRET` nothing can decrypt it. So the bootstrap paths must also exist outside Phase before
  Infisical goes away.

## Design

- **Deployment** `services/phase`: official chart `phase/phase` 1.0.2, Console **v2.79.0** (pinned), database
  `phase` on the shared PostgreSQL (`192.168.0.60`, TLS), Redis in the cluster (queue and cache only).
  The chart's Ingress is for ingress-nginx, so `access.yaml` carries Traefik routes instead: `/service/*` to
  the backend without the prefix, the rest to the frontend, HTTPS only, administration LAN only.
  URL: `https://phase.192.168.0.40.sslip.io/` (Traefik's self-signed certificate for now).
- **Login**: email and password (no SSO provider exists yet; Authentik later). No outgoing email.
- **Bootstrap secrets**: `PHASE_SECRET_KEY`, `PHASE_SERVER_SECRET`, `PHASE_REDIS_PASSWORD` (store path
  `/phase`) and `PG_APP_PHASE_PASSWORD` (`/postgresql`); `make phase-deploy` puts them into the Kubernetes
  Secret `phase-console-secret` without printing them.
- **`scripts/secrets.py`** is the workstation's entry point to the store. The store is explicit
  (`.local/secret-store` or `SECRET_STORE`: `infisical`, `phase` or `recovery`), with no default and no fallback.
  - `run /path… -- command`: run a command with those paths' secrets (replaces `infisical run …`).
  - `set /path`: create or update `KEY=VALUE` lines from standard input, read back and compared.
  - `inventory`, `migrate [--dry-run]`, `verify`: copy every Infisical secret into the Phase app
    `homelab-iac`, path by path, and compare by SHA256 of the values. Values are never printed.
  - `recovery-export`: age-encrypted copy of the bootstrap paths (`/pve-management`, `/postgresql`, `/k3s`,
    `/phase`) for the operator's recipients; `SECRET_STORE=recovery` reads it with the operator's identity.
- **Phase CLI** 2.3.3 in the workstation tool catalog (`mise`, command `phase`).

## Inventory (Infisical project Homelab-IaC, environment `dev`; `staging` and `prod` are empty)

38 keys (36 at the first inventory, plus the two Grafana passwords), all to be copied to the Phase app `homelab-iac`,
environment Development, same paths.

| Path | Keys | Used by | State |
|------|------|---------|-------|
| `/` | 10 (Proxmox tokens of the legacy roots, PVE exporter, Grafana admin, Discord webhook) | legacy roots and the legacy monitoring Compose | to copy |
| `/pve-management` | 1 | every new OpenTofu root (workstation) | to copy; bootstrap |
| `/postgresql` | 6 | `make postgresql-configure`, database passwords of Phase and Grafana | to copy; bootstrap |
| `/monitoring` | 1 | `make observability-deploy` (Grafana admin) | to copy |
| `/k3s` | 1 | `make k3s-cluster-configure` | to copy; bootstrap |
| `/phase` | 3 | `make phase-deploy` | to copy; bootstrap |
| `/headlamp` | 1 | operator login; written by `make headlamp-token` (now through `scripts/secrets.py set`) | to copy |
| `/deploy-runner` | 3 | `make deploy-runner-configure` | to copy |
| `/forgejo-runner/connections`, `/forgejo-runner/registry` | 6 + 2 | legacy CT301 runner playbooks | to copy |
| `/proxmox`, `/tailscale`, `/windmill` | 1 + 1 + 2 | legacy playbooks and scripts | to copy |

Consumers inside the repository read secrets from the environment of the command, so the switch is the
wrapper command only. Legacy targets that log in to Infisical themselves (`*_INPUT_SOURCE=infisical`:
`mgmt-*`, Stage A, Tailscale, Windmill scripts) stop working with Infisical; use `*_INPUT_SOURCE=env` under
`scripts/secrets.py run`. Consumers outside this repository are not known here: the operator confirms
before the shutdown.

## Acceptance criteria

- [x] Phase runs on k3s with its database on the shared PostgreSQL; health endpoints answer; LAN only
- [x] Offline tests for the deployment and for `scripts/secrets.py`
- [x] Infisical consumers and keys listed with their migration state
- [ ] Operator account, organisation and app `homelab-iac` exist; the workstation CLI is authenticated
- [ ] Every key copied and verified by digest (`scripts/secrets.py migrate`)
- [ ] Recovery bundle written for the operator's age recipients and opened once as a test
- [ ] Store switched to `phase`; one Make target per bootstrap path run through it
- [ ] Phase redeployed from the recovery bundle on a rebuilt cluster, or the procedure exercised without rebuild
- [ ] Infisical shut down after the operator's confirmation

## Verification

```
make phase-check
scripts/secrets.py run /postgresql /phase -- make phase-deploy PHASE_DEPLOY_APPROVED=yes
scripts/secrets.py inventory
scripts/secrets.py migrate --dry-run
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/phase.py` | pinned chart and Console, external TLS database, no in-cluster database, Traefik routes (HTTPS, LAN, prefix strip), no secret in Git, no `helm --wait` (migration hook) | `make phase-check` | PASS 2026-11-17 |
| `tests/secrets.py` | explicit store, `run` from infisical/phase/recovery, `set` with read-back, migration with digest verification and a mangled value detected, age bundle (encrypted, 0600, identity required, never overwritten by an incomplete source), no value printed | `make phase-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database | Role and database `phase` created by `make postgresql-configure` (4 changed on the primary) | Ansible recap | 2026-11-17 |
| Deploy | `make phase-deploy`: backend, worker, frontend, redis `1/1 Running`; 75 tables, 198 migrations in database `phase` | `kubectl`, `psql` | 2026-11-17 |
| Health | `/api/health` 200 `alive`; `/service/health/` 200 `v2.79.0`; `/login` 200; port 80 gives 404; from a pod 403 | `curl` | 2026-11-17 |
| CLI | `phase` 2.3.3 installed through the tool catalog | `phase --version` | 2026-11-17 |
| Store script against Infisical | `inventory` lists 12 paths / 36 keys (names only); `run /k3s` injects the token; `make headlamp-token` stored and read back the token | script output | 2026-11-17 |
| Account bootstrap | **Not done.** Automating the first sign-up with a headless browser was refused by the permission system; the owner account is the operator's to create | — | 2026-11-17 |
| Phase side of the script | **Not verified** against a real Phase (needs the account): `phase secrets import/export` are exercised only with a fake | `tests/secrets.py` | 2026-11-17 |

## Completion summary

In progress. Phase is running and empty; Infisical is still the active store (`.local/secret-store`).

Remaining: (1) operator: open `https://phase.192.168.0.40.sslip.io/`, sign up, keep the recovery kit, create
the app `homelab-iac`, then run `phase auth` on the workstation (host `https://phase.192.168.0.40.sslip.io`);
(2) operator: provide an age public key (`AGE_RECIPIENTS_FILE`) whose private key is kept outside the
homelab; (3) `scripts/secrets.py migrate`, `recovery-export`, switch `.local/secret-store` to `phase`, run
the bootstrap targets through it, update the commands in the handoff; (4) decide the certificate for
`*.192.168.0.40.sslip.io` (the CLI must verify the server it sends secrets to); (5) operator confirms the
Infisical shutdown.
