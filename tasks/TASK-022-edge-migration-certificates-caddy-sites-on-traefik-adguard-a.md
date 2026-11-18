---
id: TASK-022
title: "Edge migration: certificates, Caddy sites on Traefik, AdGuard as code"
summary: Let's Encrypt wildcard on Traefik, the active Caddy sites as Traefik routes, then AdGuard rebuilt from code and the names moved from Caddy to the cluster.
type: task
status: in-progress
priority: high
milestone: M010
created: 2026-11-18
updated: 2026-11-18
tags: [ingress, traefik, cert-manager, caddy, adguard, dns]
depends_on: [TASK-021]
related: [ARCH-platform, GUIDE-handoff]
related_decisions: [ADR-011]
related_implementations: [services/ingress, Makefile]
related_tests: [tests/ingress.py]
tests_justification: ""
verification_commands: [make ingress-check]
evidence: []
---

# TASK-022 — Edge migration: certificates, Caddy sites on Traefik, AdGuard as code

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
3. **AdGuard** (next): outside k3s, on its own small VM built from code with the same upstreams, lists and
   rewrites. Reason: the k3s nodes themselves resolve through it (image pulls), so DNS inside the cluster
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
- [ ] New AdGuard answers like the old one (rewrites, blocking, upstreams) and holds `192.168.0.20`
- [ ] Names repointed to the cluster one by one; Phase, Grafana, Headlamp on `doku-lab.net` names
- [ ] Tunnel moved; Caddy container stopped

## Verification

```
make ingress-check
scripts/secrets.py run /ingress -- make ingress-certs-deploy INGRESS_CERTS_DEPLOY_APPROVED=yes
make ingress-routes-deploy INGRESS_ROUTES_DEPLOY_APPROVED=yes
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

## Completion summary

In progress. Certificates and routes are in place and idle; no DNS answer changed yet.

Remaining: (1) AdGuard VM from code at a temporary address, compared with the old one, then the takeover of
`192.168.0.20` with the operator aware of the moment; (2) repoint the names; `doku-lab.net` names for Phase
(host change and a new CLI login), Grafana and Headlamp; (3) operator decides the names of the Proxmox UIs
and what `dropper` and `penpot` should become; (4) tunnel to k3s, stop CT204.
