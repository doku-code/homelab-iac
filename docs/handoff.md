---
id: GUIDE-handoff
title: Current handoff and next steps
summary: "Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task."
type: guide
status: current
importance: 5
created: 2026-11-14
updated: 2026-11-24
tags: [guide, handoff, workstation, pve-management]
related: [DOC-project-overview, ARCH-platform, ADR-009, ADR-010, ADR-012, ADR-014, INV-new-proxmox-cluster-inventory, INV-legacy-inventory, INV-pve-management-bootstrap, M001, M003]
topics: [handoff, current-work, workstation, state, next-task]
---

# Current handoff and next steps

Short, current state for a new session. Vision and decisions: [project overview](project-overview.md).
Update this page when the current task changes; Git keeps the history.

## How we work (operator preference)

Build the new homelab incrementally with the infrastructure we have: deploy, migrate, reclaim the
hardware, repeat. Deliver working infrastructure in small, tested, reviewable steps; reuse existing
modules, roles and Compose files; no abstraction before it is needed. **Deliberately postponed** until
the rebuild has matured: remote OpenTofu state and locking, automated or off-site backups, a disaster
recovery design, PKI, advanced secret lifecycle. Use what exists (local state, Infisical today, TrueNAS
and PBS when a migration needs a copy). Target stack and roadmap: [project overview](project-overview.md)
(k3s first, external NVMe-backed storage, TrueNAS for backups only). Basic safety stays: plan before apply, operator approval for mutations, no
secrets or state in Git, never destroy a workload before its replacement works.

## Infrastructure now

| Item | State |
|------|-------|
| New cluster `doku-lab` | Proxmox VE 9.2, quorate, 4 nodes: `pve-management` .10, `pve-core` .11, `pve-infra` .12, new `pve-lab` .16 ([inventory](investigations/new-proxmox-cluster-inventory.md)); only VM 100 exists |
| `mgmt-control-01` VM 100, 192.168.0.39 on `pve-management` | Ubuntu Desktop 26.04.1, 8 vCPU, 10 GiB, 120 GiB; OpenTofu + autoinstall + Ansible; **the operator workstation and the only OpenTofu executor** |
| `pve-compute` **192.168.0.14** | Ryzen 9 9950X3D. The old environment until 2026-11-24: emptied, separated from its one-node cluster `homelab`, renamed from `pve-lab`, upgraded and joined to `doku-lab` as its fifth node (in place, no reinstall; `.local/legacy-reset-2026-11-24.log`). Storages `local-lvm` (884 GiB) and `lab-vms` (1.8 TiB), both empty. Since 2026-11-24 it hosts both runners (VM 302 with 4 GiB, VM 303), `k3s-server-01` and `pg-03`, moved there live (`qm migrate --online --with-local-disks`, `.local/rebalance-2026-11-24.log`); `dns-01` moved from `pve-infra` to `pve-core`, so `pve-infra` hosts nothing. `storage-01` followed the same day, its disks on `lab-vms`. The token of OpenTofu has its role on `/storage/lab-vms` too (operator's word, 2026-11-25) and the root `terraform/stacks/storage` is applied: no drift. Its limit is memory: 26 of 30 GiB assigned. The token of OpenTofu has its role on `/nodes/pve-compute` (operator's word); it may not delete files, so the image copies the moved VMs came from stay on their old nodes |
| NetBox follows the cluster | A user timer on the workstation (`netbox-autosync.timer`, every 15 minutes, `make netbox-autosync-install`) reads the cluster and the hosts' own hardware and switch port and writes what changed (also whether a guest starts with its host), with the rules of `netbox-apply` (never deletes). A guest that is gone is flagged `Not on Proxmox`; removing a record stays `make netbox-prune`. Log: `journalctl --user -u netbox-autosync` |
| Legacy services | On the old host and TrueNAS: Forgejo, Nextcloud, Plex, qBittorrent, Vaultwarden, Caddy (CT204, only `git`, `cloud` and the public tunnel). The validation runner moved on 2026-11-24 to `ci-runner-01` (VM 303, 192.168.0.33, `pve-core`, root `terraform/stacks/ci-runner`, TASK-033; CT301 still exists with its runner service stopped and disabled); Vaultwarden moved to k3s on 2026-11-24 (TASK-032; the operator signed in, the old container CT206 was deleted the same day); **since 2026-11-24 the old host holds only CT301 and the stopped originals of VM 501 and 502**: the operator removed the other stopped guests (Caddy CT204, print server CT203, Garage CT209, tfstate CT300, desktop VMs, templates) before reinstalling the host to join `doku-lab`; NetBox still lists them for review. **Deleted from the old host on 2026-11-21 on the operator's word, after their replacements ran: AdGuard (CT200), Homepage (CT201), Wiki.js (CT202), Windmill (CT210), Infisical (VM 207), monitoring (VM 208), the Stage A k3s VMs (303 to 305).** Their Terraform roots (`deb13-monitoring`, `pve-lab-k3s`, `pve-core-windmill`) describe guests that no longer exist: never apply them |
| Runners | Two, by trust: `ci-runner-01` validates every repository (one Forgejo registration per repository, no infrastructure credentials, `make ci-runner-*`); `deploy-runner-01` runs the gated deployments. Adding a repository: one entry in `ci_runner_connections` (`ansible/playbooks/configure-ci-runner.yml`) and its UUID/token pair in the store path `/forgejo-runner/connections` |
| Moved from the old host, 2026-11-21 | The two Tailscale routers are the same containers on doku-lab: CT306 `ts-router-01` on `pve-core`, CT307 `ts-router-02` on `pve-management`, same addresses and Tailscale identities; their copies on the old host were deleted. No root defines them yet, and the legacy root `pve-tailscale-routers` describes where they used to be: never apply it. Two stopped Windows VMs (old 400 and 401) were copied to `pve-core` as VM 700 and 701 and stay off; the originals were deleted from the old host on 2026-11-24 on the operator's word. Two more stopped desktop VMs, 501 and 502, were copied to `pve-core` on 2026-11-24 with the same VMIDs (`vzdump` to `qmrestore`, both `exit 0`) and stay off; their originals remain on the old host until the operator says otherwise. NetBox: tunnel `tailscale-lan` with both routers, `make netbox-discover-tailscale` |
| Switch | QNAP QSW-M3216R-8S8T at 192.168.0.3. Alloy in the cluster reads its port counters over SNMPv3 every 15 s (`services/observability/snmp.yml`; sign-in in the secret store, path `/switch`, written to the Secret `switch-snmp` by `make observability-deploy`); Grafana dashboard "Switch", alert group `network` (TASK-031). The switch only has the classic interface table: no port names, no address table |

Two hosts are named `pve-lab` and `pve-lab.doku-lab.net` resolves to the old side's proxy (.24): **always
use IPs**. The new nodes have no DNS records.

## Working from mgmt-control-01

- Access: Thincast → RDP `192.168.0.39:3389`, colour depth **32 bit** and connection type LAN/auto
  (GNOME refuses clients without the RDP graphics pipeline). Stage 1: `ubuntu` + RDP password; stage 2: GDM,
  `ubuntu` + Linux password. Log out of the Proxmox console session first (one GNOME session per user).
  SSH `ubuntu@192.168.0.39` with the admin key works independently. Passwords: `.local/mgmt-control/`.
- SSH from the workstation: its own key `~/.ssh/id_ed25519` (public part `keys/mgmt-control-01.pub`) logs in
  as `ubuntu` on itself and as `root` on the four new nodes (cluster-wide `authorized_keys`). Not on `.14`.
- Repository: `~/homelab-iac`, branch `main`, `origin` = Forgejo `https://git.doku-lab.net/Homelab/homelab-iac.git`,
  `github` = push mirror (used by `mgmt-configure` as an independent source). The Forgejo wiki is generated
  from `docs/`, `milestones/`, `tasks/` and `history/` by `harness-wiki-publish.yml` on each push to `main`
  (`scripts/forgejo-wiki.py`, TASK-035): Home is `docs/home.md`, the sidebar lists the maps of `docs/hubs`
  (infrastructure, services, names, deployment, dependencies, identity, CI, decisions, operations, history).
  The maps' tables and diagrams are written by `make docs-maps` from the repository's own files; run it after
  changing what a map shows (an application, a Make target, a DNS answer, a task's status) or `make wiki-check`
  fails. Never edit wiki pages by hand.
- Tools for `ubuntu` (interactive shells, via mise): Node, Python, Go, uv, Terraform, kubectl, Helm,
  Infisical CLI, Claude Code, Codex; plus OpenTofu, SOPS, age, Docker, Git, `.venv` with Ansible and the
  harness. Zed, Obsidian, Sublime Merge in the GNOME app grid. The PVE root CA is trusted system-wide.
- OpenTofu state for `terraform/stacks/pve-management-control` lives **only here**, beside the code
  (`terraform.tfstate`, `terraform.tfvars`, 0600, git-ignored); handed over 2026-11-16, plan from here: no
  changes. The Mac copy is retired (Mac `.local/handoff/`). `make mgmt-plan` refuses to run without a state
  file, so an empty state can never recreate VM 100.
- Legacy roots: their local states (10 roots, 22 files with private tfvars) stay in place on the Mac and
  are archived, inactive, in `.local/legacy-state-archive-2026-11-16.tar` here (0600). To work on one root
  (M010), extract only that root's files into the checkout and stop using the Mac copy; Make refuses any
  legacy root whose endpoint is a new-cluster address.
- Proxmox credentials: `infisical login` once (domain `https://secrets.doku-lab.net`), then prefix Make
  targets with `scripts/secrets.py run /pve-management --` and pass `MGMT_INPUT_SOURCE=env`.
  The token's role is granted on `/vms` (every VM in the cluster, not only VM 100), `/storage/local`,
  `/storage/local-lvm`, `/nodes/pve-management`, `/nodes/pve-core` (added 2026-11-17 for VM 302) and vmbr0.
  M003 adds the runner's own `deploy-runner@pve!ci`.
- Read-only cluster audit outputs: `.local/audit/2026-11-16/`.

## First steps in the first Ubuntu session

These need the operator at the keyboard (logins, tokens); do them once, in this order:

1. `claude`: log in when prompted (Codex is installed but not used).
2. `infisical login` (choose the self-hosted domain above). Done 2026-11-17.
3. Prove state continuity with your own session (done 2026-11-17: No changes):
   `scripts/secrets.py run /pve-management -- make mgmt-plan MGMT_INPUT_SOURCE=env MGMT_ALLOCATION_REVIEWED=yes`
   must report **No changes**.
4. Forgejo push access (done 2026-11-17): a Forgejo personal access token in the credential store
   (`git config --global credential.helper store`, `~/.git-credentials` 0600); Make and agents reuse it for
   pushes and Forgejo API calls (runner registration, dispatches).

## Current and next work

- **M001 completed** 2026-11-17: Thincast two-stage login confirmed by the operator (TASK-009).
- **M002 completed**: cluster formed by the operator, audited read-only.
- **M003 completed** 2026-11-17 ([ADR-014](decisions/ADR-014-dedicated-forgejo-deployment-runner.md),
  [TASK-014](../tasks/TASK-014-bootstrap-deployment-runner-vm.md)): `deploy-runner-01`, VM 302, 192.168.0.32 on
  `pve-core` (6 vCPU / 8 GiB), Forgejo runner 10, label `homelab-deploy`; state on this workstation only, secrets
  in Infisical `dev:/deploy-runner`. Deploy flow: Forgejo → Actions → Deploy (root, `plan`) →
  `make deploy-runner-review DEPLOY_ROOT=<root>` → `make deploy-runner-approve …` → Deploy (`apply`, SHA256)
  ([runbook](../terraform/stacks/deploy-runner/README.md)). `main` is protected in Forgejo (push/merge only `doku-code`, no force-push, 2026-11-17).
- **M004 completed** 2026-11-17 ([TASK-015](../tasks/TASK-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab.md)):
  k3s `k3s-server-01`, VM 310, 192.168.0.40 on `pve-lab`, embedded etcd, Traefik + ServiceLB; `kubectl` works
  here (`~/.kube/config`, context `doku-lab`); token in Infisical `dev:/k3s`; state on this workstation only.
  Rebuild a node: `make k3s-cluster-plan K3S_CLUSTER_REPLACE=<name>` → apply → `k3s-cluster-hostkeys` →
  configure (commands in TASK-015). Add servers as tfvars entries in `terraform/stacks/k3s`.
  **Three servers since 2026-11-18** ([TASK-021](../tasks/TASK-021-k3s-servers-on-pve-core-and-pve-lab-three-etcd-members.md)):
  `k3s-server-02` (VM 311, .41, pve-core) and `k3s-server-03` (VM 312, .42, pve-lab), three etcd members,
  Traefik on every node. Since 2026-11-24 each server is on its own host (`k3s-server-01` on pve-compute): the cluster survives the loss
  of any one. **Since 2026-11-25 the kubeconfig and every published name use the shared address `192.168.0.45`**,
  held by one server at a time (kube-vip v1.3.2, ARP, manifest from `ansible/roles/k3s`; the Traefik Service has
  it as an external IP so the client address survives). Takeover measured without a failed request. Still on
  `.40`: the `*.192.168.0.40.sslip.io` names the VMs push metrics and logs to (their certificate names that address).
- **M005 completed** 2026-11-17: Headlamp at `https://headlamp.doku-lab.net/` (LAN only); sign in through Authentik, or with `HEADLAMP_ADMIN_TOKEN` (store path `/headlamp`) when Authentik is down. Redeploy: `scripts/secrets.py run /authentik -- make headlamp-deploy HEADLAMP_DEPLOY_APPROVED=yes`.
- **M006 completed** 2026-11-17 ([TASK-017](../tasks/TASK-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla.md)):
  `storage-01` (VM 350, 192.168.0.50; on `pve-compute` since 2026-11-24, both disks on its storage `lab-vms`, the 2 TB
  NVMe; moved live, operator's order) exports NFS to the k3s nodes; **user data uses
  `storageClassName: nvme-shared`** (Retain), app data may use the default `local-path`. One host, one disk,
  no backup yet. After a k3s rebuild: `make storage-csi-deploy` and `make headlamp-deploy`.
- **M007 completed** 2026-11-17 ([TASK-018](../tasks/TASK-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir.md),
  [ADR-015](decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md)): shared PostgreSQL 18 (17 until 2026-11-27, [upgrade guide](guides/postgresql-major-version-upgrade-how-the-shared-cluster-move.md)) on
  `pg-01` (VM 361, .61, pve-core), `pg-02` (VM 362, .62, pve-lab), `pg-03` (VM 363, .63, pve-compute since 2026-11-24;
  it was leader when its host rebooted that day and could not rejoin until the role allowed Patroni its own replication
  connection on localhost: it then rewound by itself, 2026-11-25) under
  Patroni with automatic failover. **Applications connect to `192.168.0.60:5432` with `sslmode=require`**,
  from the k3s nodes only. New application database: add the name to `ansible/vars/postgresql-apps.yml`,
  store `PG_APP_<NAME>_PASSWORD` in the secret store path `/postgresql`, run `make postgresql-configure`.
  State of the cluster: `make postgresql-status`. No database backups yet (M012).
- **M008 in progress** ([TASK-019](../tasks/TASK-019-phase-on-k3s-with-the-shared-postgresql-and-migration-from-i.md)):
  Phase Console v2.79.0 runs at `https://phase.doku-lab.net/` (LAN only),
  database on the shared PostgreSQL; minimum password length 10 through
  `services/phase/frontend-password-policy.yaml` (review it at every Console upgrade). **Phase is the active
  secret store** since 2026-11-18 (`.local/secret-store`; 42 keys migrated and verified):
  `scripts/secrets.py run /path… -- command`, `set /path`, `recovery-export`. Open: the operator opens the
  recovery bundle once and keeps a copy outside the homelab. Infisical (VM 207, old host) is shut down
  since 2026-11-18, not deleted.
- **Observability deployed** 2026-11-17 ([TASK-020](../tasks/TASK-020-lean-observability-prometheus-loki-grafana-and-alloy.md)):
  Grafana at `https://grafana.doku-lab.net/` (LAN only; `admin` with `GRAFANA_ADMIN_PASSWORD` from
  store path `/monitoring`), dashboard "Homelab overview". VictoriaMetrics (since 2026-11-24, [TASK-034](../tasks/TASK-034-victoriametrics-replaces-prometheus-vmalert-evaluates-the-ru.md); 90 days), vmalert and Loki on k3s; Alloy in the cluster
  and on every VM, allow-listed metrics only (about 3,900 series). Redeploy: `make observability-deploy`;
  new VM: `make observability-agents`. Alerts are posted to the operator's Discord channel by Alertmanager (webhook from the store, `DISCORD_ALERT_WEBHOOK`).
- **Edge migration in progress** 2026-11-18 ([TASK-022](../tasks/TASK-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a.md)):
  Traefik serves a Let's Encrypt wildcard for `*.doku-lab.net` (cert-manager, Cloudflare DNS-01:
  `make ingress-certs-deploy`). **LAN DNS is `dns-01`** (VM 370, `192.168.0.70`, pve-core) **with the standby `dns-02`** (VM 371, `192.168.0.71`, pve-lab,
  since 2026-11-27 after `pve-core` froze and took the LAN's only DNS with it): AdGuard Home from
  `ansible/vars/dns.yml` on both; keepalived gives `192.168.0.20` to the one that answers DNS (the primary when both do)
  and moves it in about five seconds: change a name there, then
  `scripts/secrets.py run /dns -- make dns-configure DNS_CONFIGURE_APPROVED=yes`. Eleven names go through
  Traefik (`services/ingress/legacy-routes.yaml` for the legacy backends); `git`, `cloud` and the public
  tunnel are still on the legacy Caddy (CT204). The legacy AdGuard (CT200) and the legacy monitoring VM
  (208) are stopped, not deleted. Operator rule of the day: one replica per k3s service for now.
- **NetBox deployed** 2026-11-18 ([TASK-023](../tasks/TASK-023-netbox-on-k3s-initial-inventory-reconciliation-and-ansible-i.md),
  [ADR-016](decisions/ADR-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f.md)):
  `https://netbox.doku-lab.net` (LAN only; user `admin`, password at `/netbox` in the secret store), NetBox
  4.7.5 on k3s with the shared PostgreSQL. Keep it current after a root changes: `netbox-discover` →
  `netbox-plan` → `netbox-apply` (commands below); next steps in ADR-016.
- **NetBox filled in** 2026-11-20/21 ([TASK-030](../tasks/TASK-030-netbox-as-the-full-inventory-real-hardware-ports-cables-gues.md),
  [ADR-018](decisions/ADR-018-netbox-holds-the-physical-inventory-git-says-what-a-device-i.md)): real device
  types and ports, the switch (QNAP QSW-M3216R-8S8T at 192.168.0.3 since 2026-11-22) and the access point
  (192.168.0.2), hardware of the four doku-lab hosts read by `make netbox-discover-hardware`, their cables to
  the switch as the switch announces them, roles for the old guests. **What a device is lives in
  `services/netbox/inventory.yaml`; where it sits (rack, position), asset tags and comments live in
  NetBox.** Diagrams: Topology Views and Floorplan in NetBox's menu (plugins pinned in
  `services/netbox/access.yaml`, installed on the volume `netbox-plugins`). Every root's `*-plan` target now
  checks its VMIDs and addresses against NetBox (skips itself when NetBox is away). The
  [inventory page](reference/infrastructure-inventory.md) is rewritten by `scripts/secrets.py run /netbox --
  make netbox-docs`. The rack (`rack-01`, 27 U Sysracks cabinet), pfSense's hardware (Lenovo M75q Gen 2)
  and the switch's port layout are as the operator stated them on 2026-11-21. **Open, needs the operator:**
  where each device sits in the rack (drag it in NetBox's rack view, or `position` in the file), the switch
  ports of the NAS, pfSense, the access point and the old host (`cables` in the file; automation has no
  login on the switch and only hears what the switch announces to the Proxmox hosts). 5 records still flagged
  `needs-review`: the old host, three stopped containers (print server, Garage, tfstate), the DHCP range.
- **Argo CD deployed** 2026-11-18 ([TASK-024](../tasks/TASK-024-argo-cd-on-k3s-and-netbox-as-its-first-application.md)):
  `https://argocd.doku-lab.net` (LAN only; user `admin`, password at `/argocd` in the secret store). It keeps
  the applications of `services/argocd/apps/` in sync with `main` on Forgejo (about three minutes after
  a push; it never deletes on its own): `netbox`, `headlamp`, `monitoring`, `phase`, `ingress` (cert-manager,
  certificates, routes), `storage` (NFS CSI driver), `windmill`. **A service is changed by a commit, not by `helm` or
  `kubectl apply`**: manual changes are reverted. The `<name>-deploy` Make targets now only write the Secrets
  that are not in Git and register the Application; they are needed on a rebuilt cluster or when a secret
  changes. Argo CD itself: `make argocd-deploy`. Traefik stays managed by k3s.
- **Windmill deployed** 2026-11-18 ([TASK-025](../tasks/TASK-025-windmill-on-k3s-reading-its-data-from-netbox.md)):
  `https://windmill.doku-lab.net` (LAN only; user `admin@windmill.dev`, password at `/windmill` in the secret
  store), workspace `homelab`. Scripts live in `windmill/` and are published with
  `scripts/secrets.py run /windmill -- make windmill-push`. **Automation reads infrastructure data from
  NetBox**: configuration contexts, ranges and services are defined in `services/netbox/inventory.yaml`,
  written by `netbox-apply`, and read by the scripts `f/netbox/*`. Open: a private Forgejo repository and a
  token for the scheduled NetBox export (`make netbox-export` works locally); a flow that reserves an address
  and triggers the deployment runner.
- **Authentik deployed** 2026-11-18 ([TASK-026](../tasks/TASK-026-authentik-on-k3s-and-single-sign-on-for-argo-cd-grafana-netb.md),
  [ADR-017](decisions/ADR-017-authentik-is-the-single-sign-on-of-the-platform-declared-in.md)):
  `https://auth.doku-lab.net` (LAN only; user `akadmin`, password `AUTHENTIK_BOOTSTRAP_PASSWORD` at
  `/authentik` in the secret store). Argo CD, Grafana, NetBox and Windmill sign in through it; members of
  its group `homelab-admins` are administrators everywhere; every local administrator still works.
  Applications are the blueprints of `services/authentik/blueprints`; `scripts/secrets.py run /authentik --
  make sso-check` signs in to each one and reports. The Proxmox hosts sign in through the realm
  `authentik` since 2026-11-20 (`make proxmox-sso`; `root@pam` and the tokens unchanged). Headlamp signs in
  through it since 2026-11-20: the three k3s API servers accept Authentik's identity tokens of the client
  `headlamp` (`ansible/roles/k3s/defaults`, names and groups prefixed `oidc:`), and `oidc:homelab-admins` is
  bound to cluster-admin (`services/headlamp/access.yaml`); the token login still works without Authentik.
  Open: Forgejo (left alone on the operator's word, 2026-11-20; sources
  are declared only in its administration pages or its command line), Phase (the operator links the account),
  the operator's personal account with a second factor.
- **Homepage moved to k3s** 2026-11-19 ([TASK-027](../tasks/TASK-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab.md),
  completed): `https://home.doku-lab.net` is `services/homepage` (Homepage and a widget data API), behind
  Authentik forward authentication (first use: `AUTHENTIK_FORWARD_AUTH`, embedded outpost, one outpost route
  for every name). Redeploy: `scripts/secrets.py run / /homepage -- make homepage-deploy
  HOMEPAGE_DEPLOY_APPROVED=yes`; after a change under `config/` or `metrics/`, `make homepage-k3s-check` gives
  the digest to put in `deployment.yaml`. Completed 2026-11-20: read-only Proxmox token `homepage@pve`,
  credentials of the old dashboard copied from CT201 to the store, CT201 stopped. qBittorrent shows offline
  because its application is stopped on TrueNAS.
- **Wiki on k3s** 2026-11-20 ([TASK-029](../tasks/TASK-029-wiki-js-3-on-k3s-showing-this-repository-s-documentation.md),
  completed): `https://wiki.doku-lab.net` is Wiki.js 3.5 (`services/wiki`, official chart, shared PostgreSQL,
  no volume). Its pages are this repository's documentation: `scripts/wiki-export.py` writes the page tree to
  the branch `wiki` (CI does it on every change of `main`), the wiki pulls that branch every five minutes.
  **Edit the repository, never the wiki**: a page changed in the wiki is overwritten. Redeploy:
  `scripts/secrets.py run /wiki /postgresql -- make wiki-deploy WIKI_DEPLOY_APPROVED=yes`, then
  `scripts/secrets.py run /wiki /authentik -- make wiki-configure WIKI_CONFIGURE_APPROVED=yes` (site, proxy
  trust, Git storage, Authentik sign-in, through the wiki's API). Local administrator: `admin@doku-lab.net`,
  password at `/wiki` in the store.
- **Workstation graphics** 2026-11-20 ([TASK-028](../tasks/TASK-028-workstation-vm-renders-on-the-host-s-graphics-adapter.md),
  completed): VM 100 gets the host's Intel adapter (`profile.gpu_mapping`, `make mgmt-gpu-mapping`), 12 cores
  and Proxmox protection. Running since 2026-11-20 after a failed first start (see Known issues): GNOME
  Shell went from about one core to 5 %, the host load from 4–5 to under 1.
- **Media services (test)** 2026-11-27 ([TASK-036](../tasks/TASK-036-media-stack-on-pve-infra-jellyfin-seerr-radarr-sonarr-prowla.md),
  [guide](guides/media-stack.md)): one unprivileged container per service on `pve-infra` (operator's choice of
  2026-11-26, instead of the first Compose VM): `jellyfin` 381 `.81`, `seerr` 382 `.82`, `radarr` 383 `.83`, `sonarr` 384
  `.84`, `prowlarr` 385 `.85` (root `terraform/stacks/media`, role `media_service`, native installs pinned by
  checksum). qBittorrent is the NAS's own app (`qbit-vpn`). Seerr and the three Arr tools use the shared PostgreSQL.
  The NAS's Plex library and downloads are NFS shares for `192.168.0.12`, read-only on the node and in the
  containers (`make media-mounts`); Jellyfin uses the node's graphics device. Names: `jellyfin`, `seerr` (their
  own sign-in) and `media.doku-lab.net` (the tools, behind Authentik). The first version, the VM `media-01` (380, `.80`), was deleted on 2026-11-27 on the
  operator's word. **Open:** no indexer in Prowlarr (operator's accounts). State: `make media-status`.
- **TrueNAS** 2026-11-27 ([TASK-037](../tasks/TASK-037-truenas-under-management-metrics-in-grafana-apps-as-code-hou.md),
  [guide](guides/truenas-metrics-alerts-and-apps-as-files.md)): metrics, a Grafana dashboard and alerts; the apps
  `qbit-vpn` and `plex` as files with `make truenas-plan` / `truenas-apply`. API key in the store path `/truenas`.
- **Operator roadmap (2026-11-17):** all items are deployed.

## Commands

| Purpose | Command |
|---------|---------|
| Project state | `.venv/bin/harness status` |
| Offline checks | `make mgmt-check` (all checks: `harness.yaml` verification commands) |
| Re-apply workstation config (idempotent, runs from the workstation itself) | `make mgmt-configure MGMT_CONFIGURE_APPROVED=yes MGMT_SOURCE_COMMIT=<full sha on the GitHub mirror>` |
| Add a workstation tool | one line in `ansible/roles/admin_workstation/defaults/main.yml`, then re-apply |
| Reinstall VM 100 in place | `terraform/stacks/pve-management-control/README.md` |
| Read a node | `ssh root@192.168.0.1x` (IPs only) |
| Inventory: snapshot Proxmox (read-only) | `scripts/secrets.py run /pve-management -- make netbox-discover NETBOX_SOURCE=doku-lab`; `scripts/secrets.py run / -- make netbox-discover NETBOX_SOURCE=legacy` |
| Inventory: show, then write the difference | `scripts/secrets.py run /netbox -- make netbox-plan`, then `… make netbox-apply NETBOX_APPLY_APPROVED=yes` |
| Ansible inventory from NetBox | `scripts/secrets.py run /netbox -- make netbox-inventory` |

## pfSense (read, and one change by hand)

Since 2026-11-27 the operator lets the workstation read pfSense: its `node_exporter` package is scraped (job
`pfsense`), and the key `~/.ssh/pfsense_ed25519` opens SSH as `admin`. **Nothing on pfSense is changed without the
operator's go for that change.** One change so far, on the operator's go: an upload limiter of 46 Mbit/s with
FQ-CoDel (the line is 400/50) and a floating match rule on WAN out, so that a saturated upload (qBittorrent on
the NAS) queues in pfSense, which lets small flows pass first, instead of in the modem. Record and way to put it
back: `services/pfsense/upload-limiter.php`. Backup of the configuration before it: `/root/config-before-upload-limiter.xml`
on pfSense. Verified: rule and FQ-CoDel scheduler loaded, traffic counted, download untouched. **Not verified:** the
latency while qBittorrent really fills the upload (no torrent was uploading at the time).

## Known issues

- DNS: two servers since 2026-11-27 (`dns-01` on `pve-core`, `dns-02` on `pve-lab`) share `192.168.0.20`; each keeps its own
  statistics and query log. With both down, internal names and package downloads fail.
- `pve-core` and `pve-management` lose 3 to 5 % of the full-size frames they receive in bursts (Intel I219 ports; the
  switch's counters show it sends them all):
  transfers into them from faster hosts run at 20 to 60 Mbit/s. Measurements, workaround and what is left to try:
  [known issue](issues/bursts-of-full-size-frames-are-lost-on-the-way-into-the-inte.md).
- The internet link drops for one to two minutes at a time on most days (seen in the tunnel and Tailscale
  logs since October 2026); cause not identified, pfSense is out of scope. The `netprobe` user service on
  the workstation logs each dropout per hop to `.local/netprobe.log`.
- Remote desktop from a Wi-Fi client stutters: the Wi-Fi link shows 3 to 190 ms to the client (access point: EAP720, Wi-Fi 7)
  while the wired path stays under 1 ms (measured 2026-11-22).
- Remote login after a cold boot: the service now waits for GDM (drop-in in the `admin_workstation` role); not yet
  seen through a real cold boot since.
- `pve-management` runs kernel 7.0.14-28, the other nodes -29: reboot it during approved maintenance.
- One corosync link on the shared 1 GbE LAN, one SSD per node: no physical HA yet.
- GDM allows one graphical session per user: log out of a Proxmox console desktop before RDP.
- The remote display's resolution and scaling come from the Thincast client ("Auto-fit window and
  session", 32-bit colour), not from GNOME Settings; change them in the client's connection profile.
- Docker-published ports bypass `ufw`; bind development containers to `127.0.0.1`.
- With the host GPU passed through, GNOME takes it as primary display unless
  `/etc/udev/rules.d/61-mutter-primary-gpu.rules` keeps the console adapter (bochs-drm) primary; without the
  rule the console freezes on the splash screen and remote login never opens 3389 (TASK-028). The
  `admin_workstation` role writes it when `profile.gpu_mapping` is set. A change to it restarts GDM, which
  ends all desktop and RDP sessions: run `make mgmt-configure` from SSH.
- A rollback by `make mgmt-gpu-switch` removes the GPU from the VM only: set `gpu_mapping` to null in the
  workstation's `terraform.tfvars` before the next `make mgmt-plan`, or the apply puts it back.
- Debian generic cloud images ship without `qemu-guest-agent`, while `headless-vm` enables the agent: the
  first apply of such a VM waits the full 15-minute agent timeout and only warns. `headless_baseline` installs
  the agent; until then, refreshes of that VM wait as well.
