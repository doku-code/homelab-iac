---
title: 'Wiki.js 3.4: requirements, container settings and migration from 2.x'
description: Wiki.js 3 needs PostgreSQL 17 or 18 with ltree and pg_trgm; a 2.x wiki is not upgraded in place but exported as a package from its administration area and imported into a new 3.x instance.
published: true
tags:
- library-reference
- current
- reference
- external
- wiki
- migration
editor: markdown
date: '2026-11-19T00:00:00.000Z'
dateCreated: '2026-11-19T00:00:00.000Z'
---

# Wiki.js 3.4: requirements, container settings and migration from 2.x

> **ID:** REF-wiki-js-3-4-requirements-container-settings-and-migration-fr · **Type:** library-reference · **Status:** current · **Updated:** 2026-11-19 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/reference/external/wiki-js-3-4-requirements-container-settings-and-migration-fr.md)

## Purpose

What is needed to move the legacy wiki (Wiki.js 2.x in CT202 on the old host, `wiki.doku-lab.net`, 25 pages)
to k3s. Read on 2026-11-19, before any deployment: nothing here has been run in this project yet.

## Usage in this project

Not deployed. The legacy wiki answers a guest's API request with the list of pages but not their source
[observed: project], so its content can only leave it through its administration area or its database.

## Key APIs

| Topic | Notes |
|-------|-------|
| Release state | 3.0.1 is the first stable 3.x (2026-11-01); 3.4.0 followed on 2026-11-15, five releases in two weeks. 3.x is a rewrite of backend and frontend [verified: release notes] |
| Database | PostgreSQL 17 or 18 only, extensions `ltree` and `pg_trgm` [verified: requirements]. The shared PostgreSQL is 17.12 [observed: project]; the extensions must be created in the application database by a superuser [inferred] |
| Resources | At least 1 GB of memory; image about 850 MB [verified: requirements] |
| Image | `ghcr.io/requarks/wiki`, pinned tag such as `3.4.0`; no `latest` tag in 3.x; port 3000; runs as user `wiki` [verified: installation] |
| Settings | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` or `DB_PASS_FILE`, `DB_SCHEMA` (default `wiki`), `DB_SSL`, `DB_SSL_CA` (certificate body on one line, no header or footer), or `DATABASE_URL`; `OFFLINE` stops update checks and icon downloads [verified: installation] |
| First administrator | `ADMIN_EMAIL` and `ADMIN_PASS`, read only while no root administrator exists; without them the password is a published default [verified: installation]. There is no setup wizard to automate |
| Helm chart | `oci://ghcr.io/requarks/charts/wiki`; `postgresql.enabled: false` and `externalDatabase.*` for an existing database; `admin.email`, `admin.password` [verified: installation] |
| Replicas | Several replicas may share one database, no sticky sessions needed [verified: installation]. This project runs one |
| Reverse proxy | Enable "Trust Proxy" in the administration area so the visitor's address is logged [verified: installation] |
| Sign-in through OIDC | Configured in the administration area (`/admin/auth` in the documentation); whether it can be declared as files or through an API was not read [unverified] |

## Migration from 2.x

- No in-place upgrade [verified: upgrade guide]. The procedure is: bring the 2.x wiki to 2.5.317, open
  Administration → Utilities → "Export for Wiki.js 3.x", download the `.wkbackup` package; in the new 3.x
  instance, Administration → Utilities → "Import from Wiki.js 2.x", select the package.
- Migrated: pages and content, users (not linked to a sign-in method; relinked by e-mail address at their first
  login). Not migrated: module settings (storage, authentication, comments, analytics), security and mail
  settings, logo and login background, site name. The guide does not say whether assets, page history or
  comments are carried over [unverified].
- The import can be run again; it skips what exists unless "Overwrite on conflict" is checked.
- Content to review by hand afterwards: diagrams in code blocks, draw.io diagrams, inline math, tab sets,
  relative links (they now resolve from the parent folder).

## Gotchas

- Both ends of the migration are clicks in an administration area: the old wiki's administrator signs in
  there, and the old wiki must first be upgraded inside its container. Neither is possible from this
  workstation today (no shell in CT202, no administrator credential of the old wiki in the secret store).
- Staying on 2.x instead (same version on k3s, database copied) avoids the export but leaves a version whose
  successor is out; it still needs the database of CT202.

## Verification

| Date | Method | Result |
|------|--------|--------|
| 2026-11-19 | Read the three documentation pages and the release list (GitHub API) | Facts above; nothing run |
| 2026-11-19 | Guest request to the legacy wiki's API | 25 pages listed; page source refused ("not authorized") |
