---
id: M004
title: "New compute infrastructure"
summary: "The new compute environment can reliably host and restore migrated applications."
type: milestone
status: planned
priority: high
created: 2026-11-12
updated: 2026-11-12
tags: [compute, proxmox]
related_tasks: []
related_decisions: [ADR-001]
related: [ARCH-platform]
depends_on: []
completion_criteria: []
---

# M004 — New compute infrastructure

## Objective

Establish the replacement compute environment with the available hardware.

**Completion criterion:** The new compute environment can reliably host and restore migrated applications.

## Scope

In scope:

- Prepare the remaining spare machine
- Cluster topology, quorum and networking plan
- Proxmox storage and PBS integration
- Reusable guest deployment modules
- Provisioning, backup and restore validation

Out of scope:

- HA assumptions from two nodes
- Distributed storage

## Expected deliverables

- Compute topology decision record
- Compute stack(s)
- Restore evidence

## Dependencies

- M001

## Acceptance criteria

- [ ] A guest is provisioned, backed up and restored on the new compute environment
- [ ] Quorum behaviour is documented and tested

## Verification evidence

| Criterion | Command / check | Result | Date |
|-----------|-----------------|--------|------|
| | | not verified | |

## Completion summary

_Not completed._
