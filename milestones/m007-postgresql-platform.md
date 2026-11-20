---
title: M007 — PostgreSQL platform
description: PostgreSQL 17 runs on three Patroni VMs outside k3s (one per Proxmox host) with automatic failover and a virtual IP; per-application databases and roles.
published: true
tags:
- milestone
- completed
- roadmap
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M007 — PostgreSQL platform

> **ID:** M007 · **Type:** milestone · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M007-postgresql-platform.md)

## Objective

Provide the shared relational database for Phase, Windmill, Authentik and applications.

**Completion criterion:** PostgreSQL runs on three Patroni VMs outside k3s with automatic failover, and
applications get their own database and role.

## Scope

Changed on 2026-11-17 by [ADR-015](/docs/decisions/adr-015-postgresql-runs-on-three-patroni-vms-outside-k3s):
the database servers live outside the k3s cluster instead of under an operator inside it.

In scope:

- Three PostgreSQL VMs, one per Proxmox host, Patroni + etcd, one virtual IP for applications
- Databases and roles per application, credentials outside Git

Out of scope:

- Active data on TrueNAS
- Using this PostgreSQL as the k3s datastore
- Backups (M012)

## Expected deliverables

- OpenTofu root, Ansible role, application list, Make targets

## Dependencies

- M006 (no longer a technical dependency: the data disks are VM disks, not PVCs)

## Acceptance criteria

- [x] A test database survives the loss of the primary without losing acknowledged writes
- [x] Per-application role isolation verified

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| Failover | Primary VM powered off while a pod wrote one row per second through 192.168.0.60 | Writes resumed after 37 s on `pg-02`; 180 confirmed inserts, 180 rows; old primary rejoined by `pg_rewind` | 2026-11-17 |
| Isolation | `psql` from a k3s pod as two probe roles | Own database only, TLS only; other database, no TLS and superuser refused; closed for the workstation | 2026-11-17 |

## Completion summary

Completed 2026-11-17 with [TASK-018](/tasks/task-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir).
Applications connect to `192.168.0.60:5432` (`sslmode=require`). Open points are listed in the task
(backups, trusted certificates, metrics).
