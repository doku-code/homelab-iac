---
title: 'ADR-015: PostgreSQL runs on three Patroni VMs outside k3s'
description: 'Operator decision 2026-11-17: the shared PostgreSQL platform is three Patroni VMs outside k3s with etcd and a virtual IP, not an operator inside k3s.'
published: true
tags:
- decision
- accepted
- postgresql
- patroni
- database
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-17T00:00:00.000Z'
---

# ADR-015: PostgreSQL runs on three Patroni VMs outside k3s

> **ID:** ADR-015 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md)

## Context

[ADR-013](/docs/decisions/adr-013-central-postgresql-patroni) chose one central PostgreSQL with Patroni and proposed
running it **inside** k3s with the Zalando operator. On 2026-11-17 the operator decided otherwise: database
servers live **outside the k3s cluster**, with replication and automatic failover across **three replicas**,
and every application that needs a database uses these existing servers. The k3s cluster is a single
server today and is rebuilt from IaC; a database inside it would disappear with it.

## Decision

- Three Debian 13 VMs, one per Proxmox host (`pve-core`, `pve-lab`, `pve-infra`), each with its own data
  disk: `terraform/stacks/postgresql`, role `patroni_postgresql`.
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
