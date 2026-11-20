---
id: TASK-027
title: Homepage on k3s behind Authentik, rearranged for the doku-lab cluster, with a new widget data API
summary: The dashboard moved from legacy CT201 to k3s under Argo CD, behind Authentik forward authentication, with cards for the new platform and a widget API fed by Proxmox, Prometheus and HTTP checks.
type: task
status: completed
priority: medium
milestone: M010
created: 2026-11-19
updated: 2026-11-19
tags: [homepage, dashboard, authentik, forward-auth, migration]
depends_on: [TASK-026, TASK-024]
related: [ARCH-platform, M014]
related_decisions: [ADR-017, ADR-011, ADR-012, ADR-004]
related_implementations:
  - services/homepage/
  - services/argocd/apps/homepage.yaml
  - services/authentik/blueprints/homelab-homepage.yaml
  - services/authentik/blueprints/homelab-outpost.yaml
  - services/authentik/access.yaml
  - services/ingress/legacy-routes.yaml
  - scripts/sso-check.py
related_tests:
  - tests/homepage-k3s.py
  - tests/authentik.py
  - tests/argocd.py
tests_justification: ""
verification_commands:
  - make homepage-k3s-check
  - make authentik-check
  - make argocd-check
  - scripts/secrets.py run /authentik -- make sso-check
evidence: []
---

# Homepage on k3s behind Authentik, rearranged for the doku-lab cluster, with a new widget data API

## Goal

The operator's dashboard (`https://home.doku-lab.net`) runs on k3s from this repository instead of the legacy
container CT201, shows the new platform instead of the old lab, keeps the widgets the operator built (header
summary, Proxmox node cards, status line per service, TrueNAS, Plex and qBittorrent widgets, remote desktop
launchers, background switcher) and is opened through Authentik.

## Context

- The legacy dashboard is Homepage plus a custom data API ("homelab-metrics", port 9101) in CT201 on the old
  host. Its files could not be read: no SSH access to the container, no reachable backup (the backup server
  192.168.0.15 does not answer). What it serves over HTTP was read instead: the cards, `custom.js`,
  `custom.css`, the images and the shape of `/api/snapshot`.
- The old stylesheet was 3,000 lines of layered patches that place cards by name; the old data API read
  Glances on hosts that no longer exist. Both were rewritten rather than carried over: same look and widgets,
  cards placed by Homepage's own layout, data from the new platform.
- ADR-017: an interface without a login gets forward authentication at Traefik. This is its first use.

## What was built

- `services/homepage/`: Homepage v2.8.0 (one replica, unprivileged, no Kubernetes credentials) and beside it
  the widget data API `metrics/server.py` (Python standard library on a stock image; read-only; sources in
  `metrics/sources.json`). Data: Proxmox API (node figures, guest counts, remote desktop VM state), Prometheus
  (k3s, Patroni), HTTP checks (one status line per service), and TrueNAS, Plex and qBittorrent when their
  credentials exist.
- Route `home.doku-lab.net` (LAN only, Authentik on every path; `homepage.doku-lab.net` redirects to it). The
  route to CT201 was removed from `services/ingress/legacy-routes.yaml` and from the cluster.
- Authentik: proxy provider and application `homepage` (forward authentication, open to `homelab-admins`),
  the embedded outpost's provider list as a blueprint, and one route for `/outpost.goauthentik.io/` on every
  name of the domain. `AUTHENTIK_FORWARD_AUTH` in the Makefile lists such applications; `make sso-check`
  signs in to the dashboard too.
- Outside Git: credentials (store path `/homepage`), personal links and the weather location (two values at
  `/homepage`, appended to `services.yaml` and `widgets.yaml` when the pod starts) and the background images
  (`.local/homepage/images`, copied to the volume `homepage-images` by `make homepage-images`).

## Acceptance criteria

- [x] The dashboard is served from k3s under Argo CD, one replica, LAN only
- [x] Nothing of it is served without an Authentik session; members of `homelab-admins` get in
- [x] Cards for the new platform; k3s, PostgreSQL, status lines, old-host node card and remote desktop state show live data
- [x] Nothing personal and no credential in Git
- [x] Node cards and header summary of the four doku-lab nodes show live data (read-only Proxmox token)
- [x] TrueNAS and Plex widgets show live data; the qBittorrent widget reports the application's real state (stopped on TrueNAS)
- [x] CT201 stopped (kept, not deleted)

## Verification

```
make homepage-k3s-check
make authentik-check
make argocd-check
scripts/secrets.py run /authentik -- make sso-check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| tests/homepage-k3s.py | Rendered manifests (one replica, no service account token, unprivileged, pinned images, optional secrets, files tracked by Git, restart digest), route behind Authentik, card/widget/source names agree, nothing personal in Git, widget API on canned data (templates not counted, shared storage once, Patroni lag, no contact without credentials, GET only) | `make homepage-k3s-check` | PASS 2026-11-19 |
| tests/authentik.py | Proxy provider blueprint (one name, group binding, no secret), embedded outpost serves exactly `AUTHENTIK_FORWARD_AUTH`, outpost route, forward authentication on every route of the protected name, one sign-in check per application | `make authentik-check` | PASS 2026-11-19 |
| tests/argocd.py | Nine applications, project accepts the namespace | `make argocd-check` | PASS 2026-11-19 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Deployment | Argo CD application `homepage` Synced/Healthy, pod 2/2 Running on k3s-server-03, volume bound on `nvme-shared` | `make homepage-deploy`; commits baad9f8, 264204c, 224eabe, 1736074 | 2026-11-19 |
| First sync failed | The cluster's CA certificate was named `*.pem`, which `.gitignore` excludes, so Argo CD could not build the ConfigMap. Renamed to `.crt`; the test now refuses a file Git ignores | commit 264204c | 2026-11-19 |
| Sign-in | Anonymous `GET /` and `GET /api/snapshot`: HTTP 302 to Authentik. `make sso-check`: `ok homepage HTTP 302 without a session; signed in: page HTTP 200, widget data for 5 nodes`; the four other applications still `ok` | `make sso-check` | 2026-11-19 |
| Blueprints | `Homelab - Homepage` and `Homelab - Embedded outpost` successful; outpost serves `homepage`, no Kubernetes connection | `make authentik-deploy` | 2026-11-19 |
| Live data in the pod | k3s 3/3 servers, 29/29 workloads; PostgreSQL leader pg-02, 3/3 members; 18 service checks answered (qBittorrent HTTP 502: its application is stopped on TrueNAS); old host node card live | snapshot read inside the pod; screenshot of the pod's page | 2026-11-19 |
| Rendering | Page of the pod loaded in headless Firefox: header, groups, widgets and background as designed | screenshot (not kept in Git) | 2026-11-19 |
| Read-only Proxmox token for doku-lab | not created: the session's safety check refused the credential creation; needs the operator's approval (`make homepage-pve-token HOMEPAGE_PVE_TOKEN_APPROVED=yes`). The four node cards say "not connected yet" | | 2026-11-19 |
| TrueNAS, Plex, qBittorrent widgets | not verified against the real services: their credentials exist only inside CT201. Parsing covered by the test for Plex; TrueNAS and qBittorrent calls follow their documented APIs and are untested | | 2026-11-19 |
| Read-only Proxmox token | Operator approved 2026-11-20: `homepage@pve`, `PVEAuditor`, token in the store. Four nodes online in the snapshot; summary: 48 cores, memory 55.2 %, storage 8.5 % | `make homepage-pve-token`, `make homepage-deploy`, snapshot in the pod | 2026-11-20 |
| Credentials of the old dashboard | TrueNAS key, Plex token and qBittorrent login read from the stopped CT201 (root file system mounted on the old host, read, unmounted) straight into the store at `/homepage`, never printed | `.local/legacy/pve-ssh.sh` | 2026-11-20 |
| TrueNAS widget | `online: true`, pools `fastpool` 63.9 %, `tank` 80.5 %, `apps-pool`, all `ONLINE` | snapshot in the pod | 2026-11-20 |
| Plex widget | `online: true`, 0 sessions, library 861 movies, 35 shows | snapshot in the pod | 2026-11-20 |
| qBittorrent widget | `online: false`: the application does not answer on `192.168.0.13:8080` (connection refused; TrueNAS lists one application `STOPPED`). Sign-in and transfer figures therefore not verified against the real service | curl, snapshot | 2026-11-20 |
| CT201 | Stopped since the rack restart of 2026-11-19 (no automatic start); kept on the old host | `pct status 201` | 2026-11-20 |
| Old name | `https://homepage.doku-lab.net/x` answers 302 to `https://home.doku-lab.net/x` | curl | 2026-11-19 |

## Not done

- Print server and SQL Server cards: their guests are stopped or gone; not carried over.
- Argo CD application states on the k3s card (would need a Kubernetes credential in the pod).

## Completion summary

Completed 2026-11-20. The dashboard runs on k3s behind Authentik with live data for the five Proxmox nodes,
k3s, PostgreSQL, the service checks, TrueNAS and Plex; CT201 is stopped and kept. Not verified: the qBittorrent
figures, because that application is stopped on TrueNAS; the widget shows it as offline.
