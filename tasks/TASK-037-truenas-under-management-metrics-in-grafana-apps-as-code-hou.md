---
id: TASK-037
title: "TrueNAS under management: metrics in Grafana, apps as code, housekeeping"
summary: The NAS's metrics and alerts in the monitoring stack, its apps described in the repository with a plan-before-apply path, and the leftovers of the old environment cleaned up
type: task
status: in-progress
priority: medium
milestone: M010
created: 2026-11-27
updated: 2026-11-27
tags: [truenas, monitoring]
depends_on: []
related: []
related_decisions: []
related_implementations: []
related_tests: [tests/observability.py, tests/truenas.py]
tests_justification: ""
verification_commands: [make observability-check, make truenas-check]
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

# TrueNAS under management: metrics in Grafana, apps as code, housekeeping

## Goal

The NAS (TrueNAS 25.10, 192.168.0.13) was outside the repository until 2026-11-26. The operator asked to manage it
like the rest: its metrics and alerts in the monitoring stack, its apps described in the repository with a
plan-before-apply path, and the leftovers of the old environment cleaned up. The apps stay on the NAS.
Pools, datasets, permissions and existing shares change only with the operator's word.

Access: user `homelab-iac` (Full Admin), API key in the store path `/truenas`; interface and API on HTTPS port 444.
The key must never travel over plain HTTP: TrueNAS revokes it.

## Acceptance criteria

- [x] Metrics of the NAS in VictoriaMetrics, a Grafana dashboard and alert rules (pools, disks, apps, silence).
- [x] Apps described in the repository with a plan and an approval-gated apply (`qbit-vpn`, `plex`).
- [ ] `qbit-vpn` runs the pinned digests (apply not done: the redeploy was refused by the session's permission check).
- [ ] Homepage reads the NAS without the deprecated REST API.
- [x] Timezone America/Toronto.
- [ ] bond0 replaced by its SFP+ member (two attempts rolled back, see Evidence).

## Evidence

| Date | What | Result |
|---|---|---|
| 2026-11-27 | Read-only inventory through the API | 25.10.7; pools tank, fastpool, apps-pool healthy, pve-pool offline (dead disk, to ignore); apps qbit-vpn, plex, nextcloud, forgejo running; no snapshot task, replication or cloud sync |
| 2026-11-27 | Timezone | `America/Toronto` read back |
| 2026-11-27 | Metrics exporter of the NAS repointed from 192.168.0.28 (gone) to 192.168.0.45:9109 | Graphite lines arrive; port closed for other sources |
| 2026-11-27 | `truenas-exporter.py` run against the NAS | pools, datasets, 3 disk temperatures, 4 apps, alerts by level, over the WebSocket API |
| 2026-11-27 | `make observability-check` | PASS |
| 2026-11-27 | Dashboard and rules live | Grafana lists `TrueNAS` (19 panels); 7 rules loaded, all inactive; per-disk activity joined with device names |
| 2026-11-27 | `truenas-apps.py export` of `qbit-vpn` and `plex`, then `make truenas-plan` | both "no change"; the VPN key went to the store, not the file |
| 2026-11-27 | `qbit-vpn` images pinned to the running digests, `make truenas-plan` | 2 to change (image references only); apply not run |
| 2026-11-27 | `make truenas-check` | PASS |
| 2026-11-27 | bond0 removal, twice, with TrueNAS's rollback | NAS unreachable once the address is on enp1s0 alone; rolled back by itself both times (about 1.5 and 4 minutes of outage). Not the hardware address: the bond already uses enp1s0's. Not retried blind |

## Completion summary

Remaining: apply the pinned digests to `qbit-vpn` (operator's go), describe `nextcloud`, Homepage off the REST API, the bond
(from the NAS console, or by removing only enp3s0 from it), then the media stack's use of the NAS (TASK-036).
