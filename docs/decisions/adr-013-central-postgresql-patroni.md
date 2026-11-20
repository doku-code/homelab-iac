---
title: 'ADR-013: Central PostgreSQL with Patroni'
description: Applications get their own database, role and credentials on a shared PostgreSQL platform managed by Patroni (Zalando Postgres Operator pending validation), on external NVMe-backed PVCs.
published: true
tags:
- decision
- accepted
- postgresql
- patroni
- database
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# ADR-013: Central PostgreSQL with Patroni

> **ID:** ADR-013 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-013-central-postgresql-patroni.md)

> **Changed by [ADR-015](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s) (2026-11-17):** the
> platform runs on three Patroni VMs **outside** k3s, not on k3s with the Zalando operator. The rest of this
> record (one shared platform, one database and role per application) still holds.

## Context

Phase, Windmill, Authentik and most applications need a relational database. One server per
application multiplies operations work.

## Decision

- **PostgreSQL** is the preferred relational database, run as a central platform on k3s. Each
  application gets its own database, role, scoped privileges and credentials (`phase_db`,
  `windmill_db`, `authentik_db`, …); no shared administrative user.
- **Patroni** manages replication and failover. The proposed operator is the **Zalando Postgres
  Operator**; its version and compatibility with the chosen storage and k3s are validated in M007
  before adoption.
- Start with a primary on an external NVMe-backed PVC (ADR-012), never on TrueNAS. Add standbys as
  hosts are added, one PVC each, spread across Proxmox hosts with scheduling constraints; synchronous
  or asynchronous replication chosen from the real topology. One data directory is never mounted
  read-write by two instances.
- Applications needing another PostgreSQL version, unsupported extensions or another engine get a
  separate deployment; PostgreSQL is not forced onto them.

## Consequences

- The k3s datastore is embedded etcd, never this PostgreSQL (ADR-011).
- Database-aware backups to TrueNAS are designed in M012; replication is not a backup.
