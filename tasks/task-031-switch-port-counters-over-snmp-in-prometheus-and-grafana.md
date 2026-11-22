---
title: TASK-031 — Switch port counters over SNMP in Prometheus and Grafana
description: Alloy reads the QNAP switch's interface table over SNMPv3 every 15 seconds and pushes it to Prometheus; dashboard and four alerts; sign-in from the secret store.
published: true
tags:
- task
- completed
- observability
- network
editor: markdown
date: '2026-11-22T00:00:00.000Z'
dateCreated: '2026-11-22T00:00:00.000Z'
---

# TASK-031 — Switch port counters over SNMP in Prometheus and Grafana

> **ID:** TASK-031 · **Type:** task · **Status:** completed · **Updated:** 2026-11-22 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-031-switch-port-counters-over-snmp-in-prometheus-and-grafana.md)

## Goal

See what every port of the switch carries and whether it counts errors or discards, in Grafana, with alerts,
so that network slowness can be looked at with numbers instead of guesses.

## Context

- The operator enabled SNMPv3 on the switch (192.168.0.3) on 2026-11-22; user and passwords are in the secret
  store, path `/switch` (`SWITCH_SNMP_USERNAME`, `SWITCH_SNMP_AUTH_PASSWORD`, `SWITCH_SNMP_PRIVACY_PASSWORD`,
  `SWITCH_SNMP_AUTH_PROTOCOL` SHA, `SWITCH_SNMP_PRIVACY_PROTOCOL` DES).
- What the switch answers, measured: only the system group and the classic interface table (`ifTable`). No
  64-bit counters, no address table, no neighbour table, no vendor tree; anything else returns an error, and it
  stays silent when 25 port descriptions are asked at once. Hence a module of our own
  (`services/observability/snmp.yml`) instead of the exporter's `if_mib`, without descriptions, and a reading
  every 15 seconds because the 32-bit byte counters wrap after 4 GiB.
- Collection follows the lean observability layout (TASK-020): Alloy in the cluster collects
  (`prometheus.exporter.snmp`, which embeds snmp_exporter 0.29) and pushes to Prometheus; Prometheus itself
  scrapes nothing new.

## Acceptance criteria

- [x] The sign-in is never in Git: `make observability-deploy` writes it from the environment into the Secret
  `switch-snmp`, which Alloy mounts.
- [x] Prometheus holds the state, bytes, frames, errors and discards of ports 1 to 16.
- [x] Grafana shows the dashboard "Switch".
- [x] Four alerts: switch silent, restarted, port errors, port discards.
- [x] Offline tests cover the module, the collector configuration, the sign-in helper, the dashboard and the alerts.

## Verification

```
make observability-check
scripts/secrets.py run /monitoring /postgresql /authentik /switch -- make observability-deploy OBSERVABILITY_DEPLOY_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/observability.py | The module walks only columns the switch has and holds no sign-in; every metric it reads is kept; the collector mounts the Secret; the helper quotes any password; dashboard and alerts ask only for collected metrics | `make observability-check` | PASS (2026-11-22) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Switch answers SNMPv3 | `sha: answers; sysDescr.0 = SNMPV2`; bulk requests of 25 return all 33 rows of every numeric column, the description column times out | scratch client on the workstation | 2026-11-22 |
| Deployment | `secrets applied`, Argo CD `Synced Healthy`, Alloy restarted with the volume `switch-snmp` | `make observability-deploy`, commits 903ee89 and 5da5d16 | 2026-11-22 |
| Series in Prometheus | 16 series for each of the ten port metrics, `sysUpTime` and `up`; ports 1, 3, 5, 6, 7, 8, 14 and 16 up; a rate for every one of them | query API of Prometheus | 2026-11-22 |
| Dashboard and alerts | Grafana lists `Switch` (folder Homelab, 12 panels); the four rules of group `network` are loaded, `ok`, inactive | Grafana and Prometheus APIs | 2026-11-22 |

## Completion summary

Done on 2026-11-22. Alloy reads the switch every 15 seconds; Prometheus holds the counters of the 16 ports; Grafana
has the dashboard "Switch" and Prometheus four alerts. Known limits, all the switch's: 32-bit byte counters
(a port above about 2.3 Gbit/s for a whole reading is shown too low), no port names and no address table, so the
dashboard shows port numbers and links to NetBox for what is plugged in.
