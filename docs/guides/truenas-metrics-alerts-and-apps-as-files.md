---
id: GUIDE-truenas-metrics-alerts-and-apps-as-files
title: "TrueNAS: metrics, alerts and apps as files"
summary: How the NAS is watched and how its apps are described, compared and applied from the repository
type: guide
status: current
importance: 3
created: 2026-11-27
updated: 2026-11-27
tags: [guide]
related: []
---

# TrueNAS: metrics, alerts and apps as files

The NAS (TrueNAS 25.10, `192.168.0.13`) is not built from this repository, but since 2026-11-27 it is watched and
its apps are described here ([TASK-037](../../tasks/TASK-037-truenas-under-management-metrics-in-grafana-apps-as-code-hou.md)).
The apps stay on the NAS. Pools, datasets, permissions and shares are not managed from here.

## Access

- User `homelab-iac` (Full Admin) on TrueNAS; its API key is `TRUENAS_API_KEY` in the store path `/truenas`.
- The interface and the API are on HTTPS port 444 (`wss://192.168.0.13:444/api/current`). Never send the key
  over plain HTTP (port 81): TrueNAS revokes a key it saw without TLS.
- Everything here uses the JSON-RPC API over a WebSocket. The REST API (`/api/v2.0`) is deprecated.

## Metrics, dashboard and alerts

Two sources, both read by Alloy under `job="truenas"`:

| Source | What | Where |
|---|---|---|
| Graphite stream | processor, load, memory, ZFS cache, disk and network activity, every 15 s | TrueNAS pushes to `192.168.0.45:9109` (Reporting → Exporters); `services/observability/truenas.yaml`, names in `truenas-mapping.yml` |
| API exporter | pools, datasets, disk temperatures, apps, alerts | `services/observability/truenas-exporter.py`, read-only calls, key in the Secret `truenas-api` |

- Dashboard: Grafana → **TrueNAS** (`services/observability/dashboards/truenas.json`).
- Alerts (`services/observability/vmalert.yaml`, group `truenas`): NAS silent, no metrics pushed, pool not healthy,
  pool over 85 %, disk over 50 °C, app not running, new critical alert in TrueNAS.
- `pve-pool` is left out of the pool alert: its disk died in November 2026.
- After a restart of the Graphite exporter, TrueNAS takes a few minutes to reconnect.
- Deploy: `make observability-deploy` (writes the Secret, needs the store path `/truenas` too).

## Apps as files

`services/truenas/apps/<name>.yaml` is what TrueNAS should run: a Compose project for a custom app, or the catalog
version and form values for a catalog app. Secrets are `${NAME}` placeholders filled from the store path `/truenas`.

```
scripts/secrets.py run /truenas -- make truenas-plan
scripts/secrets.py run /truenas -- make truenas-apply TRUENAS_APPS_APPROVED=yes
scripts/secrets.py run /truenas -- .venv/bin/python scripts/truenas-apps.py export <app>
```

- `plan` lists what differs, by path, without showing secret values. `apply` redeploys an app that changes.
- `TRUENAS_APPS="qbit-vpn"` limits either to the named apps.
- `export` adopts an app as it runs now. An app without a file is reported and left alone; installing or
  deleting an app is not done from here.
- Described today: `qbit-vpn` (images pinned by digest) and `plex`. `forgejo` is deliberately not described;
  `nextcloud` is not yet.
- Updating an image: put the new digest or catalog version in the file, plan, apply.

## Verification

`make truenas-check` and `make observability-check` (offline).
