---
title: M000 — Infrastructure inventory and migration planning
description: Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime.
published: true
tags:
- milestone
- active
- inventory
- planning
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-12T00:00:00.000Z'
---

# M000 — Infrastructure inventory and migration planning

> **ID:** M000 · **Type:** milestone · **Status:** active · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/M000-inventory-and-migration-planning.md)

> Roadmap 2026-11-14: the dependency map and migration order moved to M010, the PBS restore to M012. M000 keeps the repository reset and the live inventory, including the hosts' NVMe devices (needed by M002 and M006).

## Objective

Understand the existing infrastructure and establish a safe migration path.

**Completion criterion:** Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime.

## Scope

In scope:

- Repository audit and reset to the agent harness (TASK-001)
- Live, read-only inventory of Proxmox hosts, VMs, LXCs and storage
- Network/DNS dependencies, service dependency map, persistent data and backup coverage
- One representative PBS restore
- Migration order; bootstrap credential and recovery requirements

Out of scope:

- Any infrastructure change other than a disposable restore target

## Expected deliverables

- Updated INV-legacy-inventory or a new live inventory document
- Service dependency and data/backup map
- PBS restore evidence
- Migration sequence and bootstrap credential list

## Dependencies

- None

## Acceptance criteria

- [ ] Inventory verified against live systems, discrepancies resolved or recorded
- [ ] Every service has an owner, data location and backup status
- [ ] A representative PBS restore succeeded and is documented
- [ ] A migration sequence exists that never needs all machines at once

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
