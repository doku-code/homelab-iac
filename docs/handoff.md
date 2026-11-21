---
id: GUIDE-handoff
title: Current handoff and next steps
summary: "Read first in a new session: what exists, where the state lives, how to work from mgmt-control-01, the current and next task."
type: guide
status: current
importance: 5
created: 2026-11-14
updated: 2026-11-18
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
| Old environment: `pve-lab` **192.168.0.14** | Ryzen 9 9950X3D, independent, runs the legacy services; never join, rename or reconfigure it. Future `pve-compute` after M010 |
| Legacy services | On the old host and TrueNAS: Forgejo, Nextcloud, Plex, qBittorrent, Vaultwarden, Caddy (CT204, only `git`, `cloud` and the public tunnel). Still on the old host: Caddy (CT204), Vaultwarden (CT206), the migration runner (CT301), the two Tailscale routers (CT306, CT307), and stopped: print server (CT203), Garage (CT209), tfstate (CT300), the desktop VMs and templates. **Deleted from the old host on 2026-11-21 on the operator's word, after their replacements ran: AdGuard (CT200), Homepage (CT201), Wiki.js (CT202), Windmill (CT210), Infisical (VM 207), monitoring (VM 208), the Stage A k3s VMs (303 to 305).** Their Terraform roots (`deb13-monitoring`, `pve-lab-k3s`, `pve-core-windmill`) describe guests that no longer exist: never apply them |

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
  from `README.md` (Home), `docs/`, `milestones/`, `tasks/` and `history/` with a `_Sidebar` by
  `harness-wiki-publish.yml` on each push to `main`: never edit wiki pages by hand.
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
  Traefik on every node. Two members are on pve-lab (operator decision): losing pve-lab stops the API,
  losing pve-core does not. kubeconfig and the published names still use `.40`.
- **M005 completed** 2026-11-17: Headlamp at `https://headlamp.doku-lab.net/` (LAN only); sign in through Authentik, or with `HEADLAMP_ADMIN_TOKEN` (store path `/headlamp`) when Authentik is down. Redeploy: `scripts/secrets.py run /authentik -- make headlamp-deploy HEADLAMP_DEPLOY_APPROVED=yes`.
- **M006 completed** 2026-11-17 ([TASK-017](../tasks/TASK-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla.md)):
  `storage-01` (VM 350, 192.168.0.50, pve-core) exports NFS to the k3s nodes; **user data uses
  `storageClassName: nvme-shared`** (Retain), app data may use the default `local-path`. One host, one disk,
  no backup yet. After a k3s rebuild: `make storage-csi-deploy` and `make headlamp-deploy`.
- **M007 completed** 2026-11-17 ([TASK-018](../tasks/TASK-018-postgresql-platform-three-patroni-vms-outside-k3s-with-a-vir.md),
  [ADR-015](decisions/ADR-015-postgresql-runs-on-three-patroni-vms-outside-k3s.md)): shared PostgreSQL 17 on
  `pg-01` (VM 361, .61, pve-core), `pg-02` (VM 362, .62, pve-lab), `pg-03` (VM 363, .63, pve-infra) under
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
  store path `/monitoring`), dashboard "Homelab overview". Prometheus and Loki on k3s; Alloy in the cluster
  and on every VM, allow-listed metrics only (about 2,800 series with three k3s nodes). Redeploy: `make observability-deploy`;
  new VM: `make observability-agents`. Alerts are evaluated but not delivered anywhere yet.
- **Edge migration in progress** 2026-11-18 ([TASK-022](../tasks/TASK-022-edge-migration-certificates-caddy-sites-on-traefik-adguard-a.md)):
  Traefik serves a Let's Encrypt wildcard for `*.doku-lab.net` (cert-manager, Cloudflare DNS-01:
  `make ingress-certs-deploy`). **LAN DNS is `dns-01`** (VM 370, `192.168.0.70`, pve-infra; AdGuard Home from
  `ansible/vars/dns.yml`, holding `192.168.0.20`): change a name there, then
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
  types and ports, the switch (QNAP QSW-M3216R-8S8T at 192.168.0.116, a DHCP lease) and the access point
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
  login on the switch and only hears what the switch announces to the Proxmox hosts), and setting
  192.168.0.3 on the switch (it still answers at its DHCP lease 192.168.0.116). 5 records still flagged
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

## Known issues

- DNS has a single server (AdGuard 192.168.0.20 on `dns-01`); when it is down, internal names and package
  downloads fail.
- The internet link drops for one to two minutes at a time on most days (seen in the tunnel and Tailscale
  logs since October 2026); cause not identified, pfSense is out of scope. The `netprobe` user service on
  the workstation logs each dropout per hop to `.local/netprobe.log`.
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
