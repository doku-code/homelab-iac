---
id: TASK-038
title: "Shared PostgreSQL from 17 to 18: project repository, rehearsed upgrade playbook, cluster upgraded"
summary: PostgreSQL 18.7 from apt.postgresql.org on the three Patroni members; make postgresql-upgrade rehearsed on a disposable cluster, then run; the 17 data kept as the way back.
type: task
status: completed
priority: high
milestone: M007
created: 2026-11-27
updated: 2026-11-27
tags: [postgresql, patroni, upgrade]
depends_on: []
related: [GUIDE-postgresql-major-version-upgrade-how-the-shared-cluster-move, TASK-018]
related_decisions: [ADR-015]
related_implementations: [ansible/playbooks/upgrade-postgresql.yml, ansible/roles/patroni_postgresql/tasks/packages.yml, ansible/roles/patroni_postgresql/tasks/main.yml]
related_tests: [tests/postgresql.py]
tests_justification: ""
verification_commands: [make postgresql-check, make postgresql-status]
evidence: []
---

<!--
Task: the operational unit that guides an agent through one implementation step.
Create when: work spans a session boundary or needs explicit verification evidence.
Status vocabulary: planned | in-progress | blocked | completed | cancelled.
Rules:
- Never mark completed without evidence (command output, test result, commit).
- If a command failed, record the failure. If nothing was verified, write "not verified".
- Keep summaries proportional: a small task needs two factual sentences, not a log.
- A feature or fix ships with its tests in the project's test framework, written in this task and listed in
  `related_tests`. If no test is possible, say why in `tests_justification`; `harness check` refuses a completed
  task that has implementation paths but neither.
-->

# Shared PostgreSQL from 17 to 18: project repository, rehearsed upgrade playbook, cluster upgraded

## Goal

The operator asked on 2026-11-27 for the newest PostgreSQL on the shared cluster. Target: 18.7, the newest minor
of the line before the newest (19.0 was a week old and the applications' support for it was not checked). The
move must be repeatable for the next major version and must leave a way back.

## Context

- [ADR-015](../docs/decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md): three Patroni VMs outside k3s.
- [Guide](../docs/guides/postgresql-major-version-upgrade-how-the-shared-cluster-move.md): the procedure, what it leaves, the way back.
- The cluster had no backup yet (M012): the playbook takes a full dump before anything stops.

## Acceptance criteria

- [x] PostgreSQL 18 comes from the PostgreSQL project's repository; Patroni, etcd and vip-manager stay Debian's.
- [x] `make postgresql-upgrade`: gated, checks and dump first, copy mode, leader before standbys.
- [x] The role refuses to configure a member that holds data of another version only.
- [x] Upgrade and way back rehearsed on a disposable cluster with a copy of the real databases.
- [x] The real cluster runs 18.7 with three members; every application answers; configuring again changes nothing.

## Verification

```
make postgresql-check
make postgresql-status
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/postgresql.py` | package source and pin, version guard, order and safety of the upgrade plays, Make guards | `make postgresql-check` | PASS (2026-11-27) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Before | 17.12 (Debian), 15 databases, 1.4 GiB, extensions `ltree`, `pg_trgm`; Patroni 4.0.7 names PostgreSQL 18 in its release notes | leader `pg-02` | 2026-11-27 |
| Rehearsal cluster | three disposable VMs (366 to 368, `.66` to `.68`, virtual IP `.69`) from a copy of the root under `.local/`, on 17, loaded with `pg_dumpall --no-role-passwords` of the real leader | throwaway passwords | 2026-11-27 |
| Rehearsal: upgrade | no failure, 2 min 42 s; "Clusters are compatible", "Upgrade Complete"; 15 databases, 219 NetBox tables before and after; standbys streaming; `config` kept in etcd | `.local/rehearsal/upgrade-1.log` | 2026-11-27 |
| Rehearsal: way back | Patroni stopped, keys removed, old leader configured first on 17: 17.12 with 15 databases, a table written on 18 absent, both standbys streaming on the new timeline | guide, "The way back" | 2026-11-27 |
| Rehearsal VMs destroyed | "Destroy complete! Resources: 3 destroyed"; VMIDs 360 to 369 hold only `pg-01` to `pg-03` | | 2026-11-27 |
| Real run | `make postgresql-upgrade POSTGRESQL_UPGRADE_FROM=17`: no failure, 6 min 15 s | `.local/postgresql-upgrade-17-to-18.log` | 2026-11-27 |
| Downtime | Authentik's readiness not 200 from 14:39:07 to 14:40:04 UTC (57 s); Grafana 10 s | poll every 2 s | 2026-11-27 |
| After | `PostgreSQL 18.7 (Debian 18.7-1.pgdg13+5)`; leader `pg-02`, `pg-01` and `pg-03` quorum standbys streaming, lag 0; virtual IP on `pg-02`; 15 databases | `make postgresql-status` | 2026-11-27 |
| Applications | Phase (secrets read), Authentik, Grafana, Wiki.js, Vaultwarden, Windmill, Seerr answer 200; NetBox plan "0 to create, 0 to update"; Radarr, Sonarr, Prowlarr healthy; no pod outside Running | | 2026-11-27 |
| Configure again | `make postgresql-configure`: changed=0 on the three members | | 2026-11-27 |
| Monitoring | `patroni_postgres_server_version` 180007 and `pg_up` 1 on the three members | VictoriaMetrics | 2026-11-27 |
| Dump | `.local/postgresql-backups/before-upgrade-17.sql.zst`, 8.4 MB, 0600 | workstation and leader | 2026-11-27 |

## Completion summary

The cluster runs PostgreSQL 18.7. Left on purpose until the operator says so: the 17 data directory on every
member (1.4 GiB each, the way back), the package `postgresql-17`, the dump and the working directory on `pg-02`.
Not done: a restore of the dump was not tried (the rehearsal loaded a fresh `pg_dumpall` instead).
