---
id: TASK-025
title: Windmill on k3s reading its data from NetBox
summary: Deploy Windmill under Argo CD on the shared PostgreSQL, bootstrap it without default credentials, and publish scripts from Git that read roles, ranges and free addresses from NetBox.
type: task
status: completed
priority: medium
milestone: M009
created: 2026-11-18
updated: 2026-11-18
tags: [windmill, netbox, automation]
depends_on: [TASK-024, TASK-023]
related: [ARCH-platform]
related_decisions: [ADR-005, ADR-016, ADR-015, ADR-011]
related_implementations:
  - services/windmill/values.yaml
  - services/windmill/access.yaml
  - services/argocd/apps/windmill.yaml
  - scripts/windmill-admin.py
  - windmill/f/netbox/
  - scripts/netbox-sync.py
  - services/netbox/inventory.yaml
related_tests:
  - tests/windmill-k3s.py
  - tests/netbox.py
  - tests/postgresql.py
tests_justification: ""
verification_commands:
  - make windmill-k3s-check
  - make netbox-check
evidence: []
---

# TASK-025 — Windmill on k3s reading its data from NetBox

## Goal

Windmill runs on the cluster and its scripts get roles, ranges, free addresses and network settings from
NetBox through the API, so automations stop carrying their own copies of infrastructure data.

## Context

- Operator direction 2026-11-18: NetBox is the source of truth for infrastructure data; Windmill automations
  read it through the API; a copy of NetBox goes to Forgejo.
- [ADR-016](../docs/decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md) (data
  ownership), [ADR-005](../docs/decisions/ADR-005-windmill-service-catalog.md) (Windmill triggers, never
  provisions on its own).
- The Compose-based Windmill of the old environment (CT210) served nothing any more.

## Design

- **NetBox holds the parameters** as configuration contexts (per site: network; per platform: how Ansible
  logs in; per role: OpenTofu root, VMID range, allowed hosts, minimum size), address ranges tied to roles
  by IPAM roles, and services per machine. They are written from `services/netbox/inventory.yaml`: Git owns
  them, NetBox serves them merged per machine (`config_context`).
- **Export**: `scripts/netbox-sync.py export <directory>` writes every kind as a sorted YAML file without
  volatile fields, so a Git repository shows what changed in NetBox and when.
- **Windmill**: chart `windmill` 4.0.324 (Windmill CE 1.876.1) under Argo CD, one server, one script worker,
  one native worker, none privileged; database `windmill` on the shared PostgreSQL with the two helper roles
  Windmill expects (`helper_roles` in `ansible/vars/postgresql-apps.yml`).
- **No default credentials**: `make windmill-bootstrap` replaces the built-in administrator password with the
  one from the secret store, creates the workspace `homelab` and an automation token (stored at `/windmill`),
  and writes NetBox's read-only token as the secret variable `f/netbox/read_token`.
- **Scripts in Git** (`windmill/f/netbox/`), published by `make windmill-push`: `list_roles`, `next_free`
  (next free address and VMID of a role; proposes, reserves nothing), `inventory_summary`.
- Pods reach NetBox through its normal address: NetBox's route accepts the cluster's pod network besides
  the LAN (the API token is still required).

## Acceptance criteria

- [x] NetBox serves the parameters automation needs, per machine, from one API call
- [x] The whole NetBox content can be exported in a form Git can diff
- [x] Windmill deployed from the repository through Argo CD, LAN only, without default credentials
- [x] Scripts kept in Git and published from it; they read NetBox with a read-only token
- [ ] The export pushed on a schedule to a private repository on Forgejo (needs the repository and a token)
- [ ] A Windmill flow that triggers an approved runner workflow (M009)

## Verification

```
make windmill-k3s-check
scripts/secrets.py run /postgresql -- make windmill-deploy WINDMILL_DEPLOY_APPROVED=yes
scripts/secrets.py run /windmill /netbox -- make windmill-bootstrap WINDMILL_BOOTSTRAP_APPROVED=yes
scripts/secrets.py run /windmill -- make windmill-push
scripts/secrets.py run /windmill -- .venv/bin/python scripts/windmill-admin.py run f/netbox/next_free '{"role":"k3s-server"}'
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/windmill-k3s.py` | Rendered chart (pinned image, single replicas, no privileged container, database URL from the Secret, no bundled database), route, helper roles, every script (metadata, `main()`, no token in the code, NetBox read with GET only) | `make windmill-k3s-check` | PASS 2026-11-18 |
| `tests/netbox.py` | Configuration contexts (values match what the roots enforce; a change made in NetBox is overwritten), IPAM roles on ranges, services, export (sorted, no volatile fields, stable), pod network allowed on the route | `make netbox-check` | PASS 2026-11-18 |
| `tests/postgresql.py` | Helper roles cannot log in and carry no password | `make postgresql-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| NetBox parameters | 23 records created (7 contexts, 4 address roles, 12 services), 4 ranges updated; a second plan empty. The API returns for `k3s-server-02` the merged `ansible`, `network` and `provisioning` settings | `.local/netbox/apply-2.txt`, NetBox API | 2026-11-18 |
| Export | 188 records in 19 files | `make netbox-export` | 2026-11-18 |
| Database | `windmill` database and login role; `windmill_user` and `windmill_admin` (no login, `windmill_admin` bypasses row security) with `windmill` as member | `.local/postgresql-configure-windmill.log`, `pg_roles` | 2026-11-18 |
| Deployment | Application `windmill` `Synced` and `Healthy`; three pods Running; `/api/version` answers `CE v1.876.1` | `kubectl`, `curl` | 2026-11-18 |
| Image pull | One worker failed to pull: its DNS lookup hit the few seconds AdGuard restarts during `dns-configure`. The pod was recreated and started | pod events | 2026-11-18 |
| Credentials | The built-in password worked after the first start (LAN only); after `windmill-bootstrap` a login with it is refused (HTTP 400) and the stored one works | `/api/auth/login` | 2026-11-18 |
| Pods and NetBox | From a pod the LAN-only route answered 403; with the pod network added to NetBox's route the scripts read the API | `kubectl exec`, script runs | 2026-11-18 |
| Scripts | Published three; run inside Windmill: `inventory_summary` (38 machines, 10 defined in Git, 33 to review), `next_free` for `k3s-server` (192.168.0.43, VMID 313) and `postgresql` (192.168.0.64; the virtual IP .60 counts as used), `list_roles` (four roles with their ranges) | `scripts/windmill-admin.py run` | 2026-11-18 |
| Legacy Windmill | CT210 answered on no port; shut down, autostart off, not deleted | old Proxmox API | 2026-11-18 |

## Completion summary

Completed 2026-11-18 for its scope. Windmill runs at `https://windmill.doku-lab.net` (user
`admin@windmill.dev`, password at `/windmill` in the secret store) and reads NetBox.

Not done: the scheduled export to a private Forgejo repository (the operator creates the repository and a
token with write access to it; the export itself works); a flow that reserves an address and triggers the
deployment runner (M009's last criterion) — `next_free` only proposes. The script editor has no code
completion (the language-server component is not deployed). Scripts are published by `make windmill-push`,
not synchronised by Windmill itself.
