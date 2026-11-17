---
id: TASK-018
title: "PostgreSQL platform: three Patroni VMs outside k3s with a virtual IP"
summary: Three Debian 13 VMs (pg-01..03 on pve-core, pve-lab, pve-infra) run PostgreSQL 17 under Patroni with etcd and a virtual IP; per-application databases and roles.
type: task
status: completed
priority: high
milestone: M007
created: 2026-11-17
updated: 2026-11-17
tags: [postgresql, patroni, etcd, opentofu, ansible]
depends_on: []
related: [ARCH-platform, INV-new-proxmox-cluster-inventory, GUIDE-handoff]
related_decisions: [ADR-015, ADR-013, ADR-012]
related_implementations: [terraform/stacks/postgresql, ansible/roles/patroni_postgresql, ansible/playbooks/configure-postgresql.yml, ansible/vars/postgresql-apps.yml, Makefile]
related_tests: [tests/postgresql.py, terraform/stacks/postgresql/tests/postgresql.tftest.hcl]
tests_justification: ""
verification_commands: [make postgresql-check]
evidence: []
---

# TASK-018 — PostgreSQL platform: three Patroni VMs outside k3s with a virtual IP

## Goal

M007: one shared PostgreSQL for every application, outside the k3s cluster, with three replicas and
automatic failover (operator direction 2026-11-17, [ADR-015](../docs/decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md)).

## Context

- [ADR-013](../docs/decisions/ADR-013-central-postgresql-patroni.md) (one shared platform, one database and role per
  application) as changed by ADR-015 (outside k3s, three replicas with failover).
- Capacity read on 2026-11-17: free RAM pve-core ~26 GiB, pve-lab ~21 GiB, pve-infra ~5 GiB; 192.168.0.60–69
  and VMIDs 360–369 unused. Same root/role/Make pattern as `terraform/stacks/storage` (TASK-017).

## Design

- **VMs** `terraform/stacks/postgresql`: `pg-01` (VM 361, pve-core, .61, 2 vCPU / 4 GiB), `pg-02` (VM 362,
  pve-lab, .62, 2 vCPU / 4 GiB), `pg-03` (VM 363, pve-infra, .63, 2 vCPU / 2 GiB, last choice for primary).
  Each: 16 GiB OS disk plus a separate 40 GiB thin data disk (`scsi1`, mounted on `/var/lib/postgresql`;
  raise `data_disk_gb`, Ansible grows ext4). `prevent_destroy`. Reserved: VMIDs 360–369, 192.168.0.60–69.
- **Role** `patroni_postgresql` (Debian 13 packages only): PostgreSQL 17.12, Patroni 4.0.7, etcd 3.5.16 on
  the three VMs, vip-manager 3.0. Cluster name `doku-pg`. Quorum-synchronous replication (`ANY 1` of the two
  standbys), `pg_rewind`, data checksums, `failsafe_mode`. Cluster-wide settings are one variable
  (`patroni_dcs`) applied on every run.
- **Address for applications: `192.168.0.60:5432`** (virtual IP on the current primary), `sslmode=require`.
- **Access**: nftables on each VM lets only the three members reach etcd (2379/2380) and the Patroni API
  (8008), and only the members and the k3s node range 192.168.0.40–49 reach 5432. `pg_hba`: TLS + SCRAM
  only; application roles (members of the group role `app`) reach only the database named like the role;
  the superuser has the local socket only.
- **Applications**: add `- name: <app>` to `ansible/vars/postgresql-apps.yml`, store `PG_APP_<APP>_PASSWORD`
  (32+ characters) in the secret store path `/postgresql`, run `make postgresql-configure`. Nothing is ever
  dropped by the role.
- **Credentials**: `PG_SUPERUSER_PASSWORD`, `PG_REPLICATION_PASSWORD`, `PG_REWIND_PASSWORD`,
  `PG_RESTAPI_PASSWORD` in Infisical `dev:/postgresql` (generated locally, never printed); on the VMs only
  in `/etc/patroni/config.yml` (0600 postgres).
- **Limits (stated, not solved here):** self-signed server certificates (encrypted, identity not verified);
  etcd and the Patroni API rely on the VM firewalls; no watchdog; no backups until M012; `pg-03` is small.

## Acceptance criteria

- [x] Offline: root tests (4), playbook syntax, template/access/Make guard tests
- [x] Three members on three Proxmox hosts, one primary and two streaming standbys, quorum-synchronous
- [x] A test database survives the loss of the primary's VM; no acknowledged write is lost
- [x] Per-application role isolation verified from a k3s pod
- [x] The old primary rejoins as a standby without manual steps

## Verification

```
make postgresql-check
infisical run --silent --env dev --path /pve-management -- make postgresql-plan MGMT_INPUT_SOURCE=env POSTGRESQL_ALLOCATION_REVIEWED=yes
make postgresql-hostkeys
infisical run --silent --env dev --path /postgresql -- make postgresql-configure POSTGRESQL_CONFIGURE_APPROVED=yes
make postgresql-status
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `terraform/stacks/postgresql/tests/postgresql.tftest.hcl` | three members on three hosts with data disks and own image copies, inventory (virtual IP, failover priority), refusal of .14, of two members on one host, of foreign ranges and of the virtual IP as a member address | `make postgresql-check` | PASS (4) 2026-11-17 |
| `tests/postgresql.py` | etcd/vip-manager/firewall/Patroni templates, TLS + SCRAM application-only access, no network rule for the superuser, credentials 0600 and `no_log`, no re-format, nothing dropped, one-at-a-time etcd restart, reload instead of restart, Make guards | `make postgresql-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Proxmox access | Role `IaCManagementVM` granted to `tofu@pve` and its token on `/nodes/pve-infra` (same as the other nodes) | `pveum acl list` | 2026-11-17 |
| Plan / apply | 6 to add (3 image copies, VMs 361–363), 0 to change, 0 to destroy; applied; plan SHA256 `2741656e…b039` | `make postgresql-plan`, `make postgresql-apply` | 2026-11-17 |
| Host keys | Network and on-disk keys agreed on all three, pinned | `make postgresql-hostkeys` | 2026-11-17 |
| Configure | First run: etcd formed, Patroni failed to start (`python3-etcd` missing: apt satisfied the dependency with `python3-consul`); package added, second run ok; third run changed=0 | `make postgresql-configure` | 2026-11-17 |
| Cluster | `pg-01` Leader, `pg-02`/`pg-03` Quorum Standby streaming, lag 0; `synchronous_standby_names = ANY 1 ("pg-02","pg-03")`; both replication links use TLS; virtual IP on `pg-01` | `make postgresql-status`, `psql` | 2026-11-17 |
| Applications | Role created `probe_a`/`probe_b` (login, no superuser/createdb/createrole, members of `app`), databases owned by them, `PUBLIC` privileges revoked | `make postgresql-configure`, `pg_roles`, `pg_database` | 2026-11-17 |
| Isolation (from a k3s pod, through .60) | `probe_a` → own database: ok, TLSv1.3. Refused (`no pg_hba.conf entry`): `probe_a` → `probe_b`, `probe_b` → `probe_a`, no TLS, user `postgres`. Wrong password refused. Ports 2379 and 8008 closed for the pod; 5432, 2379 and 8008 closed for the workstation | `psql`, TCP probes | 2026-11-17 |
| Failover | Pod inserting one row per second; primary VM 361 powered off (`qm stop`) at 22:42:38 UTC; writes failed until 22:43:14 and succeeded from 22:43:15 (**37 s**); `pg-02` Leader on timeline 2 with the virtual IP; row written before the failover present | writer log, `make postgresql-status` | 2026-11-17 |
| No lost writes | 180 confirmed inserts in the writer log, 180 rows in the table (primary and rejoined `pg-01`) | `grep -c ok`, `select count(*)` | 2026-11-17 |
| Rejoin | VM 361 started again: Patroni ran `pg_rewind` from `pg-02` (about 80 s) and `pg-01` streams as a standby; no manual step | Patroni log, `make postgresql-status` | 2026-11-17 |
| Clean-up | Probe databases, roles, namespace and local password file removed; application list back to empty | `psql`, `kubectl`, `git status` | 2026-11-17 |

## Completion summary

Completed 2026-11-17. Applications use `192.168.0.60:5432` with `sslmode=require`, one database and role
each. The primary is currently `pg-02` (after the failover test); which member is primary does not matter
to clients. Not tested: loss of two members at once, a network partition, a restore from backup (no backups
yet).
Open: database backups (M012); trusted server certificates; metrics for replication lag and disk space
(monitoring milestone); runbook entry for replacing a dead etcd member.
