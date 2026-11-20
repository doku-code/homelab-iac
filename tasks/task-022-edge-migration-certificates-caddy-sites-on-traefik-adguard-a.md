---
title: 'TASK-022 — Edge migration: certificates, Caddy sites on Traefik, AdGuard as code'
description: Let's Encrypt wildcard on Traefik, the active Caddy sites as Traefik routes, then AdGuard rebuilt from code and the names moved from Caddy to the cluster.
published: true
tags:
- task
- in-progress
- ingress
- traefik
- cert-manager
- caddy
- adguard
- dns
editor: markdown
date: '2026-11-18T00:00:00.000Z'
dateCreated: '2026-11-18T00:00:00.000Z'
---

# TASK-022 — Edge migration: certificates, Caddy sites on Traefik, AdGuard as code

> **ID:** TASK-022 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-18 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a.md)

## Goal

Operator direction 2026-11-18: real certificates and `*.doku-lab.net` names for the platform, the bundled
Traefik as the only reverse proxy (no Caddy in front), and the legacy Caddy and AdGuard migrated first
because every other name depends on them. Services on k3s run as single replicas for now; for each service
check whether it belongs in k3s at all.

## Context

Read-only discovery of the old environment, 2026-11-18.

The operator allowed reading legacy guest configuration and stopping replaced legacy guests through the old
Proxmox host; the host itself is never changed. Copies of the files are in `.local/legacy/` (not in Git).

- **Caddy** (CT204, `192.168.0.24`): certificates through Cloudflare DNS-01. Sites in use: `cloud`, `truenas`,
  `plex`, `qbit` (TrueNAS `.13`), `homepage`/`home` (`.21`, five metric paths to port 9101), `wiki` (`.22`),
  `pbs` (`.15`, host currently off), `vault` (`.26`), `secrets` (`.27`, Infisical), `git` (`.13`, Forgejo).
  Stale: `pve-infra`, `pve-lab`, `pve-compute` (they point at `.10`, `.11`, `.12`, which are other hosts
  now) and `dropper` (its backend `192.168.0.40:666` is now a k3s node).
- **Cloudflare tunnel**: `cloudflared` runs in the same container. Public records `cloud`, `git`, `dropper`
  and `penpot` go through it, so stopping CT204 also ends public access until the tunnel is moved.
- **AdGuard Home** (CT200, `192.168.0.20`, the only DNS server of the LAN): upstreams Quad9 and Cloudflare
  over HTTPS (load balanced), DNSSEC on, three block lists (AdGuard DNS filter, AdAway, OISD Big), no
  custom rules, no per-client settings, DHCP off, 17 rewrites (13 names to Caddy, the rest direct).
  Only names with a rewrite resolve on the LAN.
- **Cloudflare token** (from Caddy): one zone, `doku-lab.net`, DNS edit and zone read. Stored in the store
  path `/ingress` and reused.
- **Legacy Grafana** (VM 208, `192.168.0.28`): shut down on the operator's instruction, autostart off.
  Start it again from the old Proxmox UI if it is missed.

## Design

1. **Certificates** (done): cert-manager (one replica per component) with a Let's Encrypt issuer over
   Cloudflare DNS-01; one wildcard `*.doku-lab.net` is Traefik's default certificate. The self-signed
   certificate for `*.192.168.0.40.sslip.io` stays selectable by name until Phase, Grafana and Headlamp
   have `doku-lab.net` names.
2. **Caddy sites on Traefik** (done, idle): `services/ingress/legacy-routes.yaml` holds one route per site in
   use, to the same backends outside k3s, with the same headers. Nothing uses them until DNS points a name
   at the cluster, so each name moves on its own and moves back by reverting one DNS answer.
3. **AdGuard** (done): outside k3s, on its own small VM (`dns-01`, VM 370, `192.168.0.70`, pve-infra, same
   AdGuard Home release as before) built from code with the same upstreams, lists and rewrites; content in
   `ansible/vars/dns.yml`, web login unchanged (hash in the store path `/dns`). Reason: the k3s nodes themselves resolve through it (image pulls), so DNS inside the cluster
   could not start after a full stop; it also needs port 53 on a fixed address. It takes over
   `192.168.0.20` at the cutover so no client and no DHCP setting changes; the old container is stopped,
   not deleted, and starting it again is the rollback.
4. **Names**: after the AdGuard cutover the rewrites live in the repository; each Caddy name is repointed to
   the cluster and checked; Phase, Grafana and Headlamp get `doku-lab.net` names.
5. **Tunnel and Caddy shutdown**: `cloudflared` moves to k3s (one replica, it only dials out) with its
   public hostnames pointed at Traefik; then CT204 is stopped.

Open: which address the names point at. For now `192.168.0.40` (first node); a shared address that moves
between nodes is deferred with the other replica questions.

## Acceptance criteria

- [x] Wildcard certificate issued and served by Traefik for `doku-lab.net` names
- [x] Every Caddy site in use answers through Traefik like through Caddy
- [x] New AdGuard answers like the old one (rewrites, blocking, upstreams) and holds `192.168.0.20`
- [x] Phase, Grafana, Headlamp on `doku-lab.net` names; nine Caddy names repointed to the cluster
- [x] `git` and `cloud` stay on the legacy Caddy for now (operator decision: services hosted on TrueNAS are handled later)
- [x] Proxmox web interfaces under their current host names; `penpot` public record deleted
- [ ] Tunnel moved; Caddy container stopped

## Verification

```
make ingress-check
scripts/secrets.py run /ingress -- make ingress-certs-deploy INGRESS_CERTS_DEPLOY_APPROVED=yes
# routes: applied by Argo CD since 2026-11-18 (services/argocd/apps/ingress.yaml)
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/ingress.py` | pinned cert-manager with single replicas and public resolvers for the DNS-01 check; issuer with the token from a Secret; wildcard as default with the sslip.io certificate kept; carried-over routes (HTTPS only, Service and address per backend, stale sites absent); no Secret in Git | `make ingress-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Token scope | One zone `doku-lab.net`: zone read, DNS records read and edit | Cloudflare API zone listing | 2026-11-18 |
| Certificate | `doku-lab-wildcard` Ready in under 3 minutes; Traefik serves `CN=*.doku-lab.net` from Let's Encrypt (until 2027-02-16) for a `doku-lab.net` name and still the self-signed certificate for the sslip.io names | `make ingress-certs-deploy`, `openssl s_client` | 2026-11-18 |
| Routes | 11 names compared through `192.168.0.24` and `192.168.0.40` with `curl --resolve`: same status and body size for all (`pbs` gives 502 on both, its host is off); the homepage metric paths answer 200 on both | `curl` | 2026-11-18 |
| Legacy Grafana | VM 208 confirmed at `192.168.0.28` by its guest agent, shut down gracefully, `onboot` 0 | old Proxmox API | 2026-11-18 |

| AdGuard build | `dns-01` created (plan 2 to add); first configure run failed on a missing drop-in directory, fixed; second run changed=21, third changed=0 | `.local/dns-*.log` | 2026-11-18 |
| AdGuard comparison | 17 of 17 local names identical on old and new; blocked names blocked on both; DNSSEC `ad` flag on both; one lookup timed out once on the new server and answered on retry, 40 paced lookups all answered | `dig` against `.20` and `.70` | 2026-11-18 |
| DNS cutover | Old container CT200 stopped (autostart off); `192.168.0.20` answered from `dns-01` 40 s later; workstation, a pod, a k3s node, a PostgreSQL member and the runner resolve | `.local/legacy/dns-cutover.sh`, `dig`, `getent` | 2026-11-18 |
| Names | `phase`, `grafana`, `headlamp`, `home`, `homepage`, `wiki`, `vault`, `secrets`, `qbit`, `truenas`, `plex` answer through `192.168.0.40` with certificate verification on (200, or the same 302/401 as before); `git` and `cloud` still through `192.168.0.24`; the secret store works through Traefik | `curl` without `-k` | 2026-11-18 |
| Phase rename | After the host change the pods kept the old name until restarted (CLI got HTTP 400); `make phase-deploy` now restarts them; the CLI reaches `https://phase.doku-lab.net` with a public certificate | `phase secrets list` with a dummy token: 401 | 2026-11-18 |

| Proxmox names | `pve-management`, `pve-core`, `pve-infra`, `pve-lab` (`.16`) answer 200 through Traefik, each page naming its own node; backend certificates verified against the cluster CA; LAN only | `curl`, `services/ingress/proxmox-routes.yaml` | 2026-11-18 |
| DNS drops under load | Operator reported an unusable network. AdGuard's default rate limit (20 answers per second, counted per /24, so shared by the whole LAN) dropped 104 of 120 simultaneous lookups; with `ratelimit: 0` 300 of 300 cached and 150 of 150 uncached lookups were answered. The old AdGuard had the same limit | burst test from the workstation, `.local/dns-configure-ratelimit.log` | 2026-11-18 |
| DNS during internet dropouts | Upstream queries hung for 30 s during dropouts (13:11–13:16, 13:20–13:21). Now: both encrypted upstreams in parallel, plain-DNS fallback, 3 s timeout, optimistic cache, private reverse lookups answered locally. Not yet observed through a real dropout | AdGuard journal, `.local/dns-configure-resilience.log` | 2026-11-18 |
| Internet link | Not caused by the lab: every guest under 1 Mbit/s during the dropouts, no duplicate addresses, DNS volume normal. The tunnel and Tailscale logs show connection losses on most days since at least early October. Cause not identified (router, modem or ISP; pfSense is out of scope). A probe on the workstation (`systemctl --user status netprobe`, `.local/netprobe.log`) records the next dropout per hop | Proxmox RRD data, legacy guest journals | 2026-11-18 |
| Infisical name | `secrets.doku-lab.net` removed from DNS and Traefik after the Infisical shutdown (TASK-019) | `kubectl -n legacy-edge get ingressroute` | 2026-11-18 |
| `penpot` | One public CNAME to the tunnel found and deleted; none left | Cloudflare API | 2026-11-18 |

## Completion summary

In progress. The LAN resolves through `dns-01`; eleven names are served by Traefik with the Let's Encrypt
wildcard; the Caddy container still serves `git`, `cloud`, the stale Proxmox names and the public tunnel.
Not carried over: the old AdGuard's query log and statistics (they stay in the stopped container).
Rollback of the DNS move: stop `dns-service-address` on `dns-01`, start CT200 on the old Proxmox host.

Remaining: (1) the services hosted on TrueNAS (`git`, `cloud`, and the tunnel that publishes them) stay on
the legacy Caddy until the operator takes them up; `dropper` is the operator's own; (2) the tunnel's entry
for `penpot` in the Cloudflare dashboard, if any, is the operator's to remove (the DNS token cannot see
tunnels); (3) move the ingestion names of the monitoring agents off sslip.io and drop the self-signed
certificate; (4) read `.local/netprobe.log` after the next internet dropout to tell router from line, then stop
the `netprobe` user service; (5) a second DNS server and a shared ingress address are deferred with the other replica
questions; `pve-compute` gets a name when that host exists.
