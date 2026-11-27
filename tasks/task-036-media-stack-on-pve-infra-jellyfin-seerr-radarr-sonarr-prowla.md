---
title: 'TASK-036 — Media stack on pve-infra: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on a Compose VM'
description: One unprivileged container per media service on pve-infra, the NAS's qBittorrent as download client; shared PostgreSQL, NAS read-only, a test area.
published: true
tags:
- task
- in-progress
- media
- jellyfin
- docker-compose
editor: markdown
date: '2026-11-27T00:00:00.000Z'
dateCreated: '2026-11-26T00:00:00.000Z'
---

# TASK-036 — Media stack on pve-infra: Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent on a Compose VM

> **ID:** TASK-036 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-27 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-036-media-stack-on-pve-infra-jellyfin-seerr-radarr-sonarr-prowla.md)

## Goal

A complete self-hosted media chain to try beside Plex (which stays on the NAS, untouched): Jellyfin, Seerr,
Radarr, Sonarr, Prowlarr and qBittorrent on one VM of `pve-infra` under Docker Compose, with the shared
PostgreSQL where the application supports it, the NAS library read-only for Jellyfin, a test area for
downloads and imports, and hardware transcoding on the host's graphics adapter. Operator's request of 2026-11-26.

## Context

- Pattern followed: a workstation root (`terraform/stacks/dns`, `storage`) plus an Ansible role; databases through
  `ansible/vars/postgresql-apps.yml`; routes outside k3s like `services/ingress/legacy-routes.yaml`; forward
  authentication like Homepage (ADR-017).
- Found before building: `pve-infra` is a Celeron N5095A (Jasper Lake) with 7.6 GiB, not an N95; the NAS exports
  nothing over NFS, refuses anonymous SMB, and no NAS account exists in the store; PostgreSQL admitted the k3s
  nodes only and a role only into the database of its own name.
- Guide for operation: [media stack](/docs/guides/media-stack).

## Acceptance criteria

- [x] VM `media-01` (380, 192.168.0.80) on `pve-infra` from `terraform/stacks/media`; data disk for configuration, cache and the test area.
- [x] Six applications from pinned images, healthy; they return by themselves after a reboot of the VM.
- [x] Seerr, Radarr, Sonarr and Prowlarr on the shared PostgreSQL over TLS (log databases for the three Arr tools); Jellyfin on SQLite on the VM.
- [x] Radarr, Sonarr and qBittorrent have no path to the NAS; their only folders are the test area; imports are hard links.
- [x] Applications connected to each other by the playbook; a second run changes nothing.
- [x] Names over HTTPS on the LAN; the four tools behind Authentik and the VM's firewall; local administrators kept.
- [x] Graphics adapter passed to the VM; a real Jellyfin session transcodes on it.
- [x] One movie and one series through the whole chain with freely licensed media.
- [x] Nightly archive of configuration and databases; restore procedure written.
- [ ] NAS library mounted read-only in Jellyfin and seen: blocked, the NAS has no export yet (operator: guide, "NAS").
- [ ] Indexers in Prowlarr: the operator's accounts.
- [ ] Playback on a real device, HEVC 10-bit and tone mapping: the operator's test.

## Verification

```
make media-check
make postgresql-check
make authentik-check
make media-status
scripts/secrets.py run /authentik -- .venv/bin/python scripts/sso-check.py media
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/media.py` | Compose project, NAS protection, graphics device, firewall, data disk guard, connections script, databases, routes, Make guards | `make media-check` | PASS 2026-11-26 |
| `terraform/stacks/media/tests/media.tftest.hcl` | VM contract, optional adapter, refused ranges and raw device | `make media-check` | 4 passed |
| `tests/postgresql.py` | further databases reachable by their role only, media VM as client | `make postgresql-check` | PASS 2026-11-26 |
| `tests/authentik.py`, `scripts/sso-check.py` | blueprint, outpost, routes ask Authentik; live sign-in | `make authentik-check`; `sso-check.py media` | PASS; `ok media` (four tools HTTP 200 after sign-in, 302 without) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| VM | `Apply complete! Resources: 2 added`; later plan: `No changes` | `make media-apply`, `make media-plan` | 2026-11-26 |
| PostgreSQL | four roles, seven databases; cluster healthy after the reload; Radarr, Sonarr, Prowlarr report `postgreSQL 17.12`; every connection `tls true` | `make postgresql-configure`, `make media-status` | 2026-11-26 |
| Applications | six containers running, health answers 200 | `make media-status` | 2026-11-26 |
| Connections | second run: `changed=0` | `make media-configure MEDIA_ANSIBLE_ARGS="--tags connect"` | 2026-11-26 |
| Firewall | LAN: 8096 and 5055 answer; 7878, 8989, 9696, 8080 do not | `curl` from the workstation | 2026-11-26 |
| Movie end to end | Seerr request (Big Buck Bunny, TMDB 10378) → Radarr → qBittorrent → imported automatically, 2 hard links → listed by Jellyfin. The torrent was handed to qBittorrent in Radarr's category by hand: no indexer exists | scratch script on the VM | 2026-11-26 |
| Series end to end | Seerr request (Pioneer One, season 1) → Sonarr → qBittorrent → `Season 1/…S01E01…`, 2 hard links → listed by Jellyfin. Same remark | scratch script on the VM | 2026-11-26 |
| Direct play | `SupportsDirectPlay=True`, file served with HTTP 206, no ffmpeg process | Jellyfin API session | 2026-11-26 |
| Hardware transcoding | limited client: ffmpeg with `-hwaccel vaapi`, `scale_vaapi`, `h264_vaapi`; adapter busy time +4.5 s; session report `vaapi`. Repeated after a reboot | Jellyfin API session; `vainfo` | 2026-11-26 |
| Reboot | first reboot: Jellyfin stayed stopped (Docker started before the render device existed). Fixed (Docker waits for the device); second reboot: six containers up by themselves | `docker ps` after `systemctl reboot` | 2026-11-26 |
| Archive | `media-<date>.tar.zst` with seven dumps, Jellyfin's SQLite copy and the configuration; copied to the workstation | `make media-backup` | 2026-11-26 |
| Restore from an archive | not verified | | |
| NAS library | not verified: no export on the NAS | `showmount -e 192.168.0.13` empty | 2026-11-26 |

## Rebuild as containers (2026-11-27)

The operator asked on 2026-11-26 for one Proxmox container per service instead of the Compose VM, and for their
existing qBittorrent on the NAS instead of a second one. What changed:

- `terraform/stacks/media`: five unprivileged containers (381 to 385, `.81` to `.85`); the VM stays in the root,
  stopped and no longer started at boot, until its deletion is approved.
- Role `media_service` replaces `media_stack`: native installs pinned by version and checksum.
- `scripts/pve-media-mounts.sh`: the NAS shares (read-only), the test area and the graphics device.
- `scripts/media-connect.py` replaces the script that ran on the VM; the download client is the NAS's qBittorrent,
  from which nothing is removed.
- PostgreSQL clients: `.82/31` and `.84/31` instead of `.80/32`. Routes: one address per service, no qBittorrent.

| Date | What | Result |
|---|---|---|
| 2026-11-27 | NFS shares on the NAS for `192.168.0.12` (`plex_media`, `downloads`), read-only, all users mapped to `apps` | mounted from pve-infra; a write is refused ("Read-only file system") |
| 2026-11-27 | `make media-plan` / `media-apply` | 6 to add, 1 to change, 0 to destroy; five containers running |
| 2026-11-27 | `make media-mounts` | library 5 entries read-only in Jellyfin; downloads read-only and test area read-write in Radarr and Sonarr; `/dev/dri/renderD128` in Jellyfin |
| 2026-11-27 | `make media-check` | PASS (7 tests, 6 mocked OpenTofu runs) |

## Completion summary

Deployed and working on the test area. Remaining: the operator adds a read-only NFS share on the NAS for
`192.168.0.80`, then `media_nas_export` and `media_nas_libraries` in `ansible/vars/media.yml` and
`make media-configure`; indexers in Prowlarr; playback on a real device. Not done on purpose: Pulsarr, a VPN in
front of qBittorrent, Alloy on the VM (memory is tight on this host), a restore drill.
