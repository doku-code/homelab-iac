---
title: 'TASK-035 — Documentation maps: hub pages generated from the repository and a wiki with a curated sidebar'
description: docs/hubs holds one map per question, with tables and diagrams generated from the repository's own files; the Forgejo wiki opens on docs/home.md and lists the maps in its sidebar.
published: true
tags:
- task
- in-progress
- documentation
- wiki
- maps
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# TASK-035 — Documentation maps: hub pages generated from the repository and a wiki with a curated sidebar

> **ID:** TASK-035 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-035-documentation-maps-hub-pages-generated-from-the-repository-a.md)

## Goal

The operator compared this repository's Forgejo wiki with the one of another repository that uses the same harness
(2026-11-25): there, the wiki opens on a home page, the sidebar lists a dozen maps ("Infrastructure map", "Service
catalog", ...) with diagrams and tables; here, Home was the README and the sidebar listed every task and decision.
Give this repository the same shape, with the facts taken from the files that already own them.

## Context

- The harness's `docs publish-wiki` builds one page per document and its own Home and sidebar (by document type);
  it has no setting for either. `scripts/forgejo-wiki.py` keeps its pages, its secret scan and its publication, and
  replaces only the navigation (it swaps `harness.wiki.build_pages`; the harness is vendored and pinned, the test
  builds the wiki through it).
- The other repository keeps a typed note per component and derives its tables from their front matter. Here the
  facts already live in machine-readable files (Argo CD applications, Makefile, `ansible/vars/dns.yml`, blueprints,
  the inventory page written from NetBox), so the maps read those instead of a second description to keep true.
  Only its structure was taken as a model; no file of it was copied.
- Wiki.js (TASK-029) publishes the same documents through `scripts/wiki-export.py`: the maps appear there under
  "Maps" without further work.

## Acceptance criteria

- [x] `docs/home.md` and eleven maps in `docs/hubs/`, each answering one question, with hand-written context and
  generated blocks (`<!-- map:NAME:start/end -->`).
- [x] `scripts/docs-maps.py` writes the blocks from files of the repository only; `--check` fails when one is stale.
- [x] The Forgejo wiki: Home from `docs/home.md`, sidebar = maps in `nav_order`, entry documents, indexes; a page
  "All pages"; every page names its source; links to repository files lead to Forgejo.
- [x] CI checks the maps before the token is read, then publishes with the new script.
- [ ] Published on the Forgejo wiki and looked at (diagrams drawn, sidebar as intended).
- [ ] Diagrams on Wiki.js looked at.

## Verification

```
make wiki-check
make docs-maps-check
.venv/bin/harness check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/wiki.py | Maps equal to the repository, every map on Home and in the sidebar in order, what the blocks read (applications, sign-in, secret paths, names, roots), no private file in a map; wiki build reproducible, Home from docs/home.md, no dead link, link rules, workflow order | `make wiki-check` | PASS 2026-11-25 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| `make wiki-check` | PASS | "documentation maps equal to the repository; Forgejo wiki reproducible with Home from docs/home.md, the maps in the sidebar and no dead link" | 2026-11-25 |
| Local build | 96 pages | `make forgejo-wiki` | 2026-11-25 |
| Publication on Forgejo | not verified | | |

## Completion summary

Remaining: push to `main`, let the workflow publish, look at the wiki (diagrams, sidebar) and at the same pages on
Wiki.js. The infrastructure map shows the inventory page as last written from NetBox (2026-11-25, before
`storage-01` was parked on `pve-lab` for the case swap of `pve-compute`); refresh with `make netbox-docs` once the
host is back and the guest is home.
