---
id: TASK-029
title: Wiki.js 3 on k3s showing this repository's documentation
summary: Wiki.js 3.5 on k3s under Argo CD with the shared PostgreSQL and Authentik sign-in; its pages are generated from this repository and pulled by the wiki's Git storage.
type: task
status: completed
priority: medium
milestone: M010
created: 2026-11-20
updated: 2026-11-20
tags: [wiki, documentation, authentik, migration]
depends_on: [TASK-024]
related: [ARCH-platform, M014, REF-wiki-js-3-4-requirements-container-settings-and-migration-fr]
related_decisions: [ADR-017, ADR-015, ADR-011]
related_implementations:
  - services/wiki/
  - services/argocd/apps/wiki.yaml
  - services/authentik/blueprints/homelab-wiki.yaml
  - scripts/wiki-export.py
  - scripts/wiki-admin.py
  - scripts/sso-check.py
  - .forgejo/workflows/harness-wiki-publish.yml
  - ansible/vars/postgresql-apps.yml
  - services/ingress/legacy-routes.yaml
related_tests:
  - tests/wiki.py
  - tests/authentik.py
  - tests/argocd.py
tests_justification: ""
verification_commands:
  - make wiki-check
  - make authentik-check
  - make argocd-check
  - scripts/secrets.py run /authentik -- make sso-check
evidence: []
---

# Wiki.js 3 on k3s showing this repository's documentation

## Goal

A wiki at `https://wiki.doku-lab.net` that is ready when the operator works on the documentation, and that
already shows the documentation of this repository. The repository stays the source: the wiki is a reader's
view of it, rebuilt from Git.

## Context

- The operator's decisions (2026-11-20): the content of the old wiki (Wiki.js 2 in CT202) is not wanted, it will
  be rewritten; the wiki should present this repository's documentation.
- Wiki.js 3 was chosen over 2.5: since the pages come from Git, nothing is lost by a later change of version,
  and 3 has probes, a first administrator from the environment and an API for every setting. It is three weeks
  old (3.0.1 on 2026-11-01, 3.5.0 on 2026-11-20); the chart and the image are pinned to 3.5.0.
- The old wiki stopped with the rack restart of 2026-11-19 and was not started again. CT202 is kept.

## What was built

- `services/wiki/`: values for the official chart (one replica, no volume, no bundled database, no Kubernetes
  credentials, offline mode), namespace and LAN-only route. Database `wiki` on the shared PostgreSQL
  (`ansible/vars/postgresql-apps.yml`; the wiki creates `ltree` and `pg_trgm` itself). Argo CD application
  `wiki`; the chart registry is declared to Argo CD.
- `scripts/wiki-export.py`: README, AGENTS, `docs/` (without the archive), `milestones/` and `tasks/` as the
  wiki's page tree: front matter the wiki reads, the title as first heading, one line with status and source
  link, links rewritten (documents to wiki paths, other files to Forgejo), one index page per folder. Pushed
  to the branch `wiki` of this repository by the existing wiki publication workflow on every change of `main`.
- `scripts/wiki-admin.py` (`make wiki-configure`): through the wiki's API as its local administrator: site
  name, trust in the proxy's headers, Git storage (pull-only from the branch `wiki`, pages only, every five
  minutes), sign-in through Authentik offered beside the local sign-in. Nothing is clicked.
- Authentik: application `wiki` open to `homelab-admins`; whoever signs in is an administrator of the wiki.
  The wiki generates the identifier in its callback address, so the address is matched by an anchored pattern.
- The route to CT202 was removed from `services/ingress/legacy-routes.yaml` and from the cluster.

## Acceptance criteria

- [x] The wiki is served from k3s under Argo CD, one replica, LAN only, on the shared PostgreSQL
- [x] It shows this repository's documentation, pulled from Git, with working links between documents
- [x] Sign-in through Authentik works; the local administrator still works
- [x] Settings are written by a tool, not by hand
- [x] A change of the documentation on `main` reaches the wiki without anyone acting (CI export, then the wiki's pull)

## Verification

```
make wiki-check
make authentik-check
make argocd-check
scripts/secrets.py run /authentik -- make sso-check
scripts/secrets.py run /wiki -- make wiki-status
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/wiki.py | Rendered chart (one replica, pinned image, no volume, no bundled database, secrets from `wiki-secrets`, encrypted database connection, offline), LAN-only route to the chart's Service, database declared, legacy route gone, export reproducible with front matter, titles and links checked on the real repository, configuration tool against an in-memory wiki (idempotent, pull-only, local sign-in kept), workflow step and Make guards | `make wiki-check` | PASS 2026-11-20 |
| tests/authentik.py | Blueprint of the wiki (callback pattern anchored to host and path), client wired on the wiki's side, one sign-in check per application | `make authentik-check` | PASS 2026-11-20 |
| tests/argocd.py | Ten applications, two chart registries declared, project accepts the namespace | `make argocd-check` | PASS 2026-11-20 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database | `wiki` created on the shared PostgreSQL (`pg-03` changed, nothing else) | `make postgresql-configure`, `.local/postgresql-configure-wiki.log` | 2026-11-20 |
| Deployment | Argo CD application `wiki` Synced/Healthy; pod `1/1 Running`; `Using PostgreSQL v17.12.0` | `make wiki-deploy`; commit 52ce0e7 | 2026-11-20 |
| Old route came back | Argo CD re-created the route to CT202 from the revision it still had when the objects were deleted, so the name answered 502. Deleted again once Argo CD had read the commit; application `ingress` Synced | kubectl | 2026-11-20 |
| Content | `Imported 82 page(s) and 0 asset(s)`; `storage: Synced; 82 pages` | `make wiki-configure` | 2026-11-20 |
| Callback address | First sign-in attempt refused by Authentik: the wiki sent an `http://` callback because it did not trust the proxy's headers. `trustProxy` is now part of `make wiki-configure` | Authentik log `redirect_uri_no_match`; commit ea02edc | 2026-11-20 |
| Sign-in | `ok wiki signed in as admin@doku-lab.net, groups ['Administrators'], administration API HTTP 200`; the six other applications still `ok` | `make sso-check` | 2026-11-20 |
| Rendering | Home page (the README), a folder index and two documents loaded in headless Firefox as a signed-in person: sidebar tree, tags, table of contents, links | screenshots (not kept in Git) | 2026-11-20 |
| Change reaches the wiki through CI | Push of ea02edc to `main`: the workflow pushed `docs: export of ea02edc…` to the branch `wiki` (jobs `check`, `publish`, `validate` all success); the wiki showed the changed title of TASK-028 80 seconds later without being asked; 82 pages | Forgejo Actions runs 243–245, wiki API | 2026-11-20 |

## Not done

- A visitor who is not signed in sees no page (the wiki's default). The LAN restriction and the sign-in are
  both in place; opening the pages to every LAN visitor would be a setting of the wiki's groups.
- People who sign in get the wiki's Administrators group whatever their Authentik groups, because only
  `homelab-admins` may open the application. A second group would need a mapping.
- Pages edited in the wiki are overwritten at the next pull: the repository is the source.

## Completion summary

Completed 2026-11-20. The wiki runs on k3s, shows 82 pages generated from this repository, follows `main`
through CI and its own pull, and signs people in through Authentik beside its local administrator. The old
wiki (CT202) is stopped and kept; its content was not carried over.
