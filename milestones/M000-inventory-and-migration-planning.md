---
id: M000
title: "Infrastructure inventory and migration planning"
summary: "Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime."
type: milestone
status: active
priority: critical
created: 2026-11-12
updated: 2026-11-14
tags: [inventory, planning]
related_tasks: [TASK-001, TASK-002]
related_decisions: [ADR-001, ADR-007]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M000 — Infrastructure inventory and migration planning

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
