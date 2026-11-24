---
title: TASK-032 — Vaultwarden on k3s with its vault in the shared PostgreSQL
description: Vaultwarden moves from the container on the old host to k3s; its SQLite vault is copied into the shared PostgreSQL; same name, same account.
published: true
tags:
- task
- completed
- vaultwarden
- migration
editor: markdown
date: '2026-11-24T00:00:00.000Z'
dateCreated: '2026-11-24T00:00:00.000Z'
---

# TASK-032 — Vaultwarden on k3s with its vault in the shared PostgreSQL

> **ID:** TASK-032 · **Type:** task · **Status:** completed · **Updated:** 2026-11-24 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-032-vaultwarden-on-k3s-with-its-vault-in-the-shared-postgresql.md)

## Goal

Take the password manager off the old host: the same Vaultwarden, the same account and items, under the same
name, on k3s with its data in the shared PostgreSQL (ADR-015).

## Context

- Before: a Docker container (`vaultwarden/server:latest`, running 1.37.2) in CT206 on the old host, SQLite,
  reached through a Traefik route to 192.168.0.26. One account, 234 items, one attachment.
- The new deployment pins 1.37.2, the version the data came from, so the PostgreSQL schema it creates matches.
- Vaultwarden has no tool to change database: the tables were copied one by one (script kept in
  `.local/vaultwarden-migration/`, with the export, until the operator has signed in), parents before children,
  integers turned into booleans where the target column is one. PostgreSQL only accepts the cluster, so the
  copy ran from a temporary pod.
- No single sign-on: the vault is unlocked by its own master password; the administration page is off.

## Acceptance criteria

- [x] One pinned replica on k3s, database on the shared PostgreSQL, key and attachments on the NVMe-backed volume.
- [x] Every row of the old vault is in the new database.
- [x] `vault.doku-lab.net` answers from the new deployment, LAN only.
- [x] The operator signs in with the existing account and sees the items (operator's check).
- [x] Offline tests.

## Verification

```
make vaultwarden-check
scripts/secrets.py run /postgresql -- make vaultwarden-deploy VAULTWARDEN_DEPLOY_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/vaultwarden.py | Pinned image, one replica, database address only from the Secret, registration and administration page off, LAN-only route, old route gone, Argo CD application and Make guards | `make vaultwarden-check` | PASS (2026-11-24) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database | role and database `vaultwarden` created on the shared PostgreSQL | `make postgresql-configure` | 2026-11-24 |
| Data copy | `users: 1, ciphers: 234, devices: 10, folders: 2, twofactor: 1, attachments: 1, folders_ciphers: 25`, `loaded 274 rows in 28 tables`, each table's count equal to the source | loader in a temporary pod | 2026-11-24 |
| Files | the old signing key and the one attachment are on the new volume | `ls /data` in the pod | 2026-11-24 |
| Service | `alive 200` through 192.168.0.40, `/api/config` names Vaultwarden at `https://vault.doku-lab.net`, web vault 200 | curl from the workstation | 2026-11-24 |
| Sign-in with the existing account | first refused with `502`: the route `legacy-edge/vault` to the old container was still in the cluster (removed from Git, never pruned) and won; deleted, then `vault.doku-lab.net/alive` 200 six times and the operator signed in (clients had to log in again: `Issuer is invalid` for the old sessions) | operator, 2026-11-24; logs of the pod | 2026-11-24 |
| Old copy removed | `pct destroy 206` `exit 0`; `.local/vaultwarden-migration/` deleted | `.local/legacy-destroy-2026-11-24.log` | 2026-11-24 |

## Completion summary

Done on 2026-11-24: the vault is served from k3s with its data in the shared PostgreSQL, the operator signed in, the
old container CT206 and the local export are deleted. There is no dump of the vault database yet beyond PostgreSQL's
own replicas (backups are deferred).
