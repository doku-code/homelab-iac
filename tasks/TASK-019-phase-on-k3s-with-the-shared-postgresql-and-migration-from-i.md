---
id: TASK-019
title: Phase on k3s with the shared PostgreSQL and migration from Infisical
summary: Phase Console v2.79.0 runs on k3s with its database on the shared PostgreSQL; scripts/secrets.py selects the store, migrates and verifies; cutover waits for the operator's Phase account.
type: task
status: in-progress
priority: high
milestone: M008
created: 2026-11-17
updated: 2026-11-18
tags: [phase, secrets, infisical, k3s, migration]
depends_on: [TASK-018]
related: [ARCH-platform, GUIDE-handoff]
related_decisions: [ADR-004, ADR-015, ADR-011]
related_implementations: [services/phase, services/phase/frontend-password-policy.yaml, scripts/secrets.py, ansible/vars/postgresql-apps.yml, ansible/roles/admin_workstation/defaults/main.yml, Makefile]
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
  URL: `https://phase.doku-lab.net/` since 2026-11-18 (Let's Encrypt wildcard, TASK-022).
- **Certificate** (operator approval 2026-11-18): one self-signed certificate for `*.192.168.0.40.sslip.io`
  (not a CA, server authentication only, until 2028-11-17) is Traefik's default certificate
  (`services/ingress/tls-store.yaml`, `make ingress-tls-deploy`). Its public part is `keys/k3s-ingress.crt`,
  trusted system-wide on the workstation (`configure-mgmt-control.yml`); its key is in the store path
  `/ingress`, which is a bootstrap path. The Phase CLI therefore verifies the server.
- **Login**: email and password (no SSO provider exists yet; Authentik later). No outgoing email.
  Minimum password length **10** instead of Phase's built-in 16 (operator decision 2026-11-18). Phase has no
  setting for it and checks the length only in the browser, so `services/phase/frontend-password-policy.yaml`
  makes the frontend container rewrite that rule in its own files before it starts; the container stops if
  the expected code is missing, so a Console upgrade that changes it fails the rollout and has to be reviewed.
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
    `/ingress`, `/phase`) for the operator's recipients; `SECRET_STORE=recovery` reads it with the operator's identity.
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
- [x] Operator account, organisation and app `homelab-iac` exist; the workstation CLI is authenticated
- [x] Every key copied and verified by digest (`scripts/secrets.py migrate`)
- [ ] Recovery bundle written for the operator's age recipients (done) and opened once as a test (operator)
- [x] Store switched to `phase`; Make targets run through it
- [ ] Phase redeployed from the recovery bundle on a rebuilt cluster, or the procedure exercised without rebuild
- [x] Infisical shut down after the operator's confirmation

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
| `tests/phase.py` (password rule) | the start-up patch turns 16 into 10 in the three code shapes of v2.79.0, leaves unrelated length checks alone, and exits without starting when the code is missing or changed | `make phase-check` | PASS 2026-11-18 |
| `tests/secrets.py` | explicit store, `run` from infisical/phase/recovery, `set` with read-back, migration with digest verification and a mangled value detected, age bundle (encrypted, 0600, identity required, never overwritten by an incomplete source), no value printed | `make phase-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database | Role and database `phase` created by `make postgresql-configure` (4 changed on the primary) | Ansible recap | 2026-11-17 |
| Deploy | `make phase-deploy`: backend, worker, frontend, redis `1/1 Running`; 75 tables, 198 migrations in database `phase` | `kubectl`, `psql` | 2026-11-17 |
| Health | `/api/health` 200 `alive`; `/service/health/` 200 `v2.79.0`; `/login` 200; port 80 gives 404; from a pod 403 | `curl` | 2026-11-17 |
| CLI | `phase` 2.3.3 installed through the tool catalog | `phase --version` | 2026-11-17 |
| Store script against Infisical | `inventory` lists 12 paths / 36 keys (names only); `run /k3s` injects the token; `make headlamp-token` stored and read back the token | script output | 2026-11-17 |
| Password rule | Patched frontend rolled out; the served sign-up code says "at least 10 characters" (28 fields, 4 checks, 2 meters rewritten; nothing left at 16); `/signup`, `/login`, `/api/health` 200. Not tested by creating an account | `kubectl patch`, `curl` over the served chunks | 2026-11-18 |
| Operator account | One user, one organisation, app `homelab-iac` exist (read-only count in database `phase`) | `psql` on the primary | 2026-11-18 |
| CLI login | **Missing on the workstation**: the CLI refused Traefik's generated certificate (`x509: certificate is valid for …traefik.default`) | `phase secrets list` with a dummy token | 2026-11-18 |
| Ingress certificate | Deployed; `curl` without `-k` gets 307/302/200 from Phase, Grafana, Headlamp and 200 through .41 and .42; the CLI now reaches the server (401 for the dummy token); 8 hosts still push metrics | `make ingress-tls-deploy`, `curl`, PromQL | 2026-11-18 |
| Recovery bundle | Written from Infisical for the operator's recipient (`keys/operator-recovery.age.pub`): 5 bootstrap paths. Not opened: the identity is the operator's | `scripts/secrets.py recovery-export` | 2026-11-18 |
| Migration | 42 keys on 15 paths copied to the Phase app `homelab-iac` (Development); every path `ok` by SHA256 of the values, and again in a separate `verify` run | `.local/phase-migrate-1.log`, `scripts/secrets.py verify` | 2026-11-18 |
| Store switch | `.local/secret-store` is `phase`; through it: `k3s-cluster-plan` (No changes), `dns-configure` (changed=0), `ingress-tls-deploy` (unchanged), `headlamp-token` | Make output | 2026-11-18 |
| Updating a key | First attempt failed: `phase secrets import` refuses an existing key (HTTP 409). `scripts/secrets.py` now imports new keys and updates existing ones with the value on standard input; create-then-update checked against the real Phase on a throw-away path | `tests/secrets.py`, probe path | 2026-11-18 |
| Recovery bundle from Phase | Rewritten from Phase: 5 bootstrap paths. Not opened here: only the operator holds the identity | `scripts/secrets.py recovery-export` | 2026-11-18 |
| Infisical shutdown | Operator confirmed. VM 207 on the old host shut down gracefully, `onboot` 0, not deleted; `scripts/secrets.py run` and `dns-configure` work through Phase afterwards; `verify` and `migrate` no longer apply (they read Infisical) | old Proxmox API, Make output | 2026-11-18 |
| Account bootstrap | **Not done.** Automating the first sign-up with a headless browser was refused by the permission system; the owner account is the operator's to create | — | 2026-11-17 |
| Phase side of the script (before the account existed) | **Not verified** against a real Phase (needs the account): `phase secrets import/export` are exercised only with a fake | `tests/secrets.py` | 2026-11-17 |

## Completion summary

In progress. **Phase is the only store** since 2026-11-18: Infisical (VM 207 on the old host) is shut down,
autostart off, not deleted. Legacy targets with `*_INPUT_SOURCE=infisical` need `*_INPUT_SOURCE=env` under
`scripts/secrets.py run`.

Remaining: (1) operator: open the recovery bundle once (`age -d -i <identity> .local/recovery/secrets.json.age`)
and keep a copy of the bundle and the Phase recovery kit outside the homelab; (2) Phase redeployed from the
recovery bundle on a rebuilt cluster, or the procedure exercised without a rebuild.
