---
id: TASK-023
title: NetBox on k3s, initial inventory, reconciliation and Ansible inventory
summary: Deploy NetBox with the official chart on the shared PostgreSQL, populate it from the OpenTofu outputs and read-only Proxmox discovery, and let Ansible read its inventory from it.
type: task
status: completed
priority: medium
milestone: M013
created: 2026-11-18
updated: 2026-11-18
tags: [netbox, inventory, ipam]
depends_on: [TASK-018, TASK-017, TASK-022]
related: [ARCH-platform, REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll]
related_decisions: [ADR-016, ADR-015, ADR-012, ADR-011]
related_implementations:
  - services/netbox/values.yaml
  - services/netbox/access.yaml
  - services/netbox/inventory.yaml
  - scripts/netbox-sync.py
  - ansible/inventories/netbox.yml
  - Makefile
related_tests:
  - tests/netbox.py
tests_justification: ""
verification_commands:
  - make netbox-check
evidence: []
---

# TASK-023 — NetBox on k3s, initial inventory, reconciliation and Ansible inventory

## Goal

NetBox is deployed from this repository, holds a first inventory that separates what Git defines from what
was only observed, can be reconciled again safely, and serves one existing automation workflow.

## Context

- [ADR-016](../docs/decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md):
  architecture, data ownership, alternatives.
- Patterns reused: Phase deployment (pinned chart, Secret from the environment, Traefik route, LAN only),
  application databases in `ansible/vars/postgresql-apps.yml`, DNS answers in `ansible/vars/dns.yml`.
- [Reference](../docs/reference/external/netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll.md):
  chart, API and collection behaviour found on the way.

## Design

- `services/netbox/values.yaml` + `access.yaml`: chart 8.3.107 (NetBox 4.7.5), one web pod (two workers),
  one worker pod, external PostgreSQL `192.168.0.60` database `netbox` (TLS required), media on
  `nvme-shared` (ReadWriteMany), official Valkey 9.1.3 in the cluster, login required, route
  `netbox.doku-lab.net` for the LAN.
- `services/netbox/inventory.yaml`: site, clusters, roles, platforms, prefix, ranges, physical devices
  (seed), extra addresses, and the list of OpenTofu roots whose VMs are inventoried.
- `scripts/netbox-sync.py`: `discover` (read-only Proxmox snapshot), `plan`, `apply`, `identities`. Standard
  library and PyYAML only. It has no delete call.
- `ansible/inventories/netbox.yml`: `netbox.netbox.nb_inventory`, VMs tagged `iac`, existing group names.
- Make: `netbox-check`, `netbox-deploy`, `netbox-identities`, `netbox-discover`, `netbox-plan`,
  `netbox-apply`, `netbox-inventory`; `observability-agents OBS_INVENTORY=netbox`.

## Acceptance criteria

- [x] Architecture chosen and recorded with its alternatives (ADR-016)
- [x] NetBox deployed from the repository and reachable on the LAN with a valid certificate; no anonymous access
- [x] Credentials only in the secret store and a Kubernetes Secret; two scoped service accounts
- [x] Initial inventory written after a reviewed plan; verified and unverified records distinguishable
- [x] A second reconciliation changes nothing; nothing is deleted or overwritten outside the fields Git owns
- [x] One existing workflow runs from NetBox's inventory with the same result as before
- [x] Existing workflows unchanged by default; nothing needs NetBox to bootstrap

## Verification

```
make netbox-check
scripts/secrets.py run /netbox /postgresql -- make netbox-deploy NETBOX_DEPLOY_APPROVED=yes
scripts/secrets.py run /pve-management -- make netbox-discover NETBOX_SOURCE=doku-lab
scripts/secrets.py run / -- make netbox-discover NETBOX_SOURCE=legacy
scripts/secrets.py run /netbox -- make netbox-plan
scripts/secrets.py run /netbox -- make netbox-inventory
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/netbox.py` | Rendered chart (pinned image, single replicas, external database with TLS, no bundled sub-chart, no Secret in the output, login required, shared media volume), Valkey and route manifests, Make guards and Secret keys, reconciliation against an in-memory NetBox (plan writes nothing, apply then plan is empty, seed and discovered records are not overwritten, a person's tags survive, address conflicts and vanished guests are reported, no delete, stale snapshot refused), read-only discovery including a token without `Sys.Audit`, seed and inventory file rules | `make netbox-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Database | `netbox` database and role created by the existing role (`postgresql-configure` changed only the new application); Patroni: leader `pg-02`, two standbys, VIP on the leader | `.local/postgresql-configure-netbox.log`, `make postgresql-status` | 2026-11-18 |
| Deployment | Release `netbox` installed; migrations ran against the shared PostgreSQL over TLS; pods `netbox`, `netbox-worker`, `netbox-valkey` Running; `/api/status/` reports 4.7.5 and one worker; media volume `192.168.0.50:/srv/k3s/netbox/netbox-media` writable | `.local/netbox-deploy-1.log`, `kubectl -n netbox get pods` | 2026-11-18 |
| Memory | The web pod used 1.5 GiB with the image's four workers; set to two and redeployed (rollout completed) | `.local/netbox-deploy-2.log`, `kubectl top` | 2026-11-18 |
| Access | `https://netbox.doku-lab.net/login/` 200 with the wildcard certificate; API without a token 403 | `curl` | 2026-11-18 |
| Superuser token | First attempt failed: the chart passes a superuser token, the image ignores it without a key (`Invalid v1 token`). `identities` now provisions a ten-minute token from the password; the unused store key was deleted | NetBox log, `scripts/netbox-sync.py` | 2026-11-18 |
| Service accounts | `inventory-sync` (view, add, change on 16 models) and `automation-read` (view) created; tokens stored at `/netbox`. The read token got 403 on a write and sees only its own token entry | `make netbox-identities`, `curl` | 2026-11-18 |
| Discovery | Legacy host: cluster `homelab`, 28 guests. New cluster: 10 guests; the provisioning token may not read the cluster name (`Sys.Audit`), discovery falls back to the node list | `.local/netbox/observed-*.json` | 2026-11-18 |
| Plan | 165 to create, nothing deleted; 14 review lines (13 guests without a static address in their Proxmox configuration, and the stopped legacy AdGuard container still carrying `192.168.0.20`, which `dns-01` serves). The seed's "printer at .23" was wrong: discovery showed a stopped `print-server` container there; seed entry removed | `.local/netbox/plan-2.txt` | 2026-11-18 |
| Apply and repeat | 165 created; a second plan: `0 to create, 0 to update` | `.local/netbox/apply-1.txt`, `plan-3.txt` | 2026-11-18 |
| Content | 9 devices (5 Proxmox hosts with firmware-reported hardware, 4 unmanaged devices of unknown model; 5 flagged `needs-review`), 2 clusters, 38 VMs (10 `iac`, 28 `discovered` + `needs-review`), 35 addresses, 1 prefix, 5 ranges | NetBox API with the read token | 2026-11-18 |
| Ansible inventory | 10 hosts in 6 groups from NetBox; name, group, address, user, VMID and Proxmox host identical to the six OpenTofu inventories | `make netbox-inventory`, comparison script | 2026-11-18 |
| Existing workflow | `observability-agents` through NetBox's inventory: 8 hosts, `changed=0`, `failed=0`. In check mode both inventories give the same task-by-task result, including the same failure on the three PostgreSQL members (a condition in the monitoring-role task that cannot be evaluated in check mode; it predates this task) | `.local/netbox/agents-*.log` | 2026-11-18 |
| Bootstrap independence | The default `observability-agents` (OpenTofu inventories) and every root's own targets do not read NetBox | Makefile | 2026-11-18 |

## Completion summary

Completed 2026-11-18. NetBox 4.7.5 runs on k3s at `https://netbox.doku-lab.net`, holds the first inventory
and serves the Ansible inventory for runs across roots.
Since the same day NetBox is installed and kept in sync by Argo CD
([TASK-024](TASK-024-argo-cd-on-k3s-and-netbox-as-its-first-application.md)); `make netbox-deploy` only writes its Secret.

Not done, on purpose (ADR-016, next steps): no address allocation from NetBox during provisioning, no
OpenTofu provider, no services, cables, racks or MAC addresses, no Kubernetes workloads. Operator: review the
34 records tagged `needs-review` in NetBox (5 devices, 28 legacy guests, the DHCP range) and fill in what only a person
knows (hardware of router, switch, NAS; addresses of guests that set them inside the guest). The admin
password is in the secret store at `/netbox` (`NETBOX_SUPERUSER_PASSWORD`, user `admin`).
