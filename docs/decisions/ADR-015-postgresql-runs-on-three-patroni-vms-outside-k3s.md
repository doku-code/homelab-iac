---
id: ADR-015
title: PostgreSQL runs on three Patroni VMs outside k3s
summary: "Operator decision 2026-11-17: the shared PostgreSQL platform is three Patroni VMs outside k3s with etcd and a virtual IP, not an operator inside k3s."
type: decision
status: accepted
importance: 5
created: 2026-11-17
updated: 2026-11-17
tags: [decision, postgresql, patroni, database]
component: database
topics: [postgresql, patroni, etcd, database, replication, failover]
related: [ARCH-platform, ADR-013, ADR-012, ADR-011]
related_tasks: [TASK-018]
related_milestones: [M007]
supersedes: []
superseded_by: []
---

# ADR-015: PostgreSQL runs on three Patroni VMs outside k3s

## Context

[ADR-013](ADR-013-central-postgresql-patroni.md) chose one central PostgreSQL with Patroni and proposed
running it **inside** k3s with the Zalando operator. On 2026-11-17 the operator decided otherwise: database
servers live **outside the k3s cluster**, with replication and automatic failover across **three replicas**,
and every application that needs a database uses these existing servers. The k3s cluster is a single
server today and is rebuilt from IaC; a database inside it would disappear with it.

## Decision

- Three Debian 13 VMs, one per Proxmox host (`pve-core`, `pve-lab`, `pve-infra`), each with its own data
  disk: `terraform/stacks/postgresql`, role `patroni_postgresql`.
- *(Update 2026-11-27: PostgreSQL itself is 18 from the PostgreSQL project's repository since [TASK-038](../../tasks/TASK-038-shared-postgresql-from-17-to-18-project-repository-rehearsed.md); the rest stays Debian's.)*
- **PostgreSQL 17, Patroni 4, etcd 3.5 and vip-manager from Debian's own packages** (security updates
  through the distribution, no extra repository). etcd runs on the same three VMs.
- **Quorum-synchronous replication**: a commit waits for one of the two standbys, so a failover loses no
  acknowledged transaction; with both standbys down the primary keeps accepting writes.
- Applications connect to one **virtual IP, 192.168.0.60:5432**, which follows the primary.
- Each application gets one database and one login role **of the same name**
  (`ansible/vars/postgresql-apps.yml`), password from the secret store. Access is TLS + SCRAM only, from the
  k3s node range only, and only to the database named like the role. The superuser has no network access.
- What stays from ADR-013: one shared platform, per-application database and role, Patroni, never on
  TrueNAS, not the k3s datastore, separate deployment only for applications that need another engine.

## Alternatives considered

- **Zalando operator inside k3s (ADR-013)** — ties the database to the cluster's life and to its storage;
  rejected by the operator decision above.
- **HAProxy or PgBouncer in front** — a second moving part per node; one virtual IP is enough at this size.
  A pooler can be added later without changing the address.
- **keepalived for the address** — VRRP could collide with other VRRP/CARP users on the LAN; vip-manager
  only follows Patroni's leader key.

## Consequences

- Three more VMs to patch; `pg-03` on `pve-infra` is small (2 GiB) and is the last choice for primary.
- TLS uses each VM's self-signed certificate: traffic is encrypted, the server identity is not verified
  (`sslmode=require`). A trusted certificate comes with the certificate decision for the platform.
- etcd and the Patroni API have no authentication of their own for reads; the VM firewalls restrict them to
  the three members.
- No watchdog device is configured, and replication is not a backup: database backups come with M012.
- Changing a setting that needs a PostgreSQL restart leaves the members "pending restart"; restart them
  one at a time with `patronictl restart doku-pg --pending`.
