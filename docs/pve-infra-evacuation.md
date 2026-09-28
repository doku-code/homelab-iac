# pve-infra evacuation assessment

Task [150](../tasks/150-pve-infra-evacuation.md), read-only evidence collected
2026-09-28, approximately10:08-10:15 UTC. Recommendations are NOT migration
approval. No guest, storage, credentials, network or cluster membership changed.
No Terraform state, application database or private user data inspected; no
credential values or full configurations retrieved/exported. Public summary only.

## Verified identity and host responsibilities

- Strict known-host SSH to the inventory address192.168.0.10 confirmed hostname
  pve-infra/member ID3, distinct from pve-compute. AZW MINI S, Celeron N5095A,
  4 cores/4 threads;7719MiB usable RAM,4863MiB available at observation.
- One256GB nominal SATA SSD with local LVM-thin; no redundant disk observed.
  Proxmox9.2.11/kernel7.0.14-14-pve, matching pve-core's observed versions.
- Four online one-vote members: core/compute/infra/lab; expected/total votes4,
  quorum3, quorate. No configured HA resources or replication jobs returned.
- vmbr0/nic0 at1Gb/s full duplex, .10/24, gateway192.168.0.1; Wi-Fi down.
  CTs share vmbr0; destination bridge/firewall parity still needs cutover checks.
- **Tailscale subnet router:** forwarding enabled, advertises192.168.0.0/24,
  primary LAN route peer. No other advertiser returned in this host's peer view;
  tailnet-wide approvals/ACLs/failover unverified. Host uses Tailscale DNS.
  Moving CTs will not move this remote-access responsibility.
- Host Glances/node-exporter, SSH and Proxmox services active. Timer names
  inspected; cron directories contain4/5 files, no user crontabs. Custom cron
  contents/external automation not audited; review before sale.

## Guest inventory and destinations

All five CTs run/onboot on local-lvm:44GiB root disks allocated, about12GiB
filesystem usage. All except203 explicitly unprivileged;201/202/204 nesting
enabled. Preserve behavior, not a recommendation to add these privileges.
No extra mp/dev bindings observed except203's raw LXC device/mount entries.
Sizes below are configured limits, not measured peaks. All LAN addresses /24.

| CT / function | vCPU / RAM / disk; IP | Observed runtime and preservation needs | Recommended destination and gate |
| --- | --- | --- | --- |
| 200 AdGuard | 1 /512MiB /8GiB; .20 | AdGuardHome active, DNS53/UI80; /opt/AdGuardHome config/data. DHCP disabled;18 rewrite answers. Preserve users/filtering/rewrites and selected history | **B: core, outside K8s initially.** Preserve IP/identity; independent DNS/admin fallback and client tests first |
| 201 Homepage + metrics | 1 /512MiB /8GiB; .21 | Two healthy Docker containers on3000/9101. Homepage latest; custom homelab-metrics image has no tags/RepoDigests. Binds /opt/homepage/config, public/images, metrics-api, metrics-cache | **B: core interim**, possible future A. Preserve widget access/config, custom code/image and cache semantics; prove both dashboard and metrics |
| 202 Wiki.js | 1 /2048MiB /16GiB; .22 | Wiki.js2, postgres17-alpine healthy, HTTP80. PG volume wiki-js_db-data, anonymous content volume, read-only GitHub-key bind under /opt/wiki-js/keys/github | **B: core interim**, possible future A after storage qualification. Consistent DB/content/config/auth/Git identity recovery before move |
| 203 printing | 1 /256MiB /4GiB; .23 | CUPS/Avahi/cups-browsed,631/mDNS; queue transport USB. Privileged; bindings /dev/bus/usb, /dev/usb/lp0, /run/udev and device permissions | **C: outside K8s**; core only after approved physical USB relocation. Preserve queues/drivers/config, verify permissions and real print |
| 204 Caddy + tunnel | 2 /1024MiB /8GiB; .24 | Caddy/cloudflared active;80/443, loopback admin. Caddyfile/data present,14 proxy directives. Standard checked cloudflared locations lacked config/credential files; actual source unknown | **B: core initially**, independent of K8s. Locate runtime-input source metadata safely; preserve TLS/account/tunnel identity and test every route |

Exact versions/digests, data consistency and authentication dependencies need a
focused pre-cutover manifest. A running service is not a recoverable service.

## Dependencies and ownership

- Caddy proxies Proxmox UIs, TrueNAS-hosted endpoints, PBS, Homepage/metrics,
  Wiki.js, Vaultwarden and Infisical. NAS/Git/OCI/secrets published access can fail
  while their data remains elsewhere. No end-to-end route/tunnel tests performed.
- AdGuard rewrite IPs include .20/.23/.24/.25/.30; other CTs explicitly use .20,
  as do repository guest profiles. DHCP clients/all consumers/fallback unverified.
- Homepage references hypervisors, TrueNAS and LAN services; the metrics helper
  prevents treating this as a proven disposable static dashboard.
- Shared NFS pve_library consumes TrueNAS(.13); shared PBS(.15), backup-store,
  active from infra/core. Infra is a client, not an observed storage server.
  All five CT disks are local and require transfer/restore, not shared-disk reuse.
- No active Terraform root/service Ansible role found owning CT200-204. Current
  authority is Proxmox/manual configuration; no permission to import/recreate.
  Preserve IDs/data/IPs on approved relocation where practical. No state migration.
- Later cleanup includes the pve-infra Ansible host, Prometheus .10:9100, Caddy
  infra UI route and Homepage references. Keep them until cutovers are accepted.

## Backups and recovery gaps

Enabled cluster job: snapshot/03:00/PBS/keep-all; includes200/202/204 and existing
core guests, no node restriction returned. Five latest infra vzdump tasks report
OK. No schedule/retention changes or backups/restores were executed.

| CT | Visible PBS snapshots | Latest creation UTC | Current job inclusion |
| --- | --- | --- | --- |
| 200 | 7 | 2026-09-28 07:00:01 | Yes |
| 201 | 6 | 2026-09-22 07:00:56 | **No** |
| 202 | 7 | 2026-09-28 07:00:59 | Yes |
| 203 | 6 | 2026-09-22 07:03:47 | **No** |
| 204 | 7 | 2026-09-28 07:02:44 | Yes |

Metadata/task OK does not prove archive integrity, application-consistent restore,
offsite independence or acceptable RPO. No restore evidence found for these CTs
in inspected repository documentation. Fresh201/203 protection and isolated tests
require approval. Wiki.js needs consistent PG/content recovery, not snapshot alone.

## pve-core capacity

Observed Ryzen7 6800H8C/16T,30.6GiB usable RAM,15.8GiB available, zero swap used;
load0.38/0.35/0.27. Guests206/207/208/209/300/400 remain: Vaultwarden, Infisical,
monitoring, Garage, tfstate and Windows services. Configured RAM totals17.73GiB.
Destination vmbr0 is on the same LAN/gateway. Local-lvm has about380GiB free of
429GiB; root filesystem only22GiB free, unsuitable for assuming44GiB staging room.

Five CTs add4.25GiB RAM/6 vCPU, roughly22GiB configured guest RAM total on core.
This is **plausible, not capacity approval**. Reserve host overhead, existing
critical peaks, transfer/restore space and future active K3s server capacity.
Thin free space/idle CPU are not guarantees. Consolidation increases the common
failure domain of DNS, edge and applications; retain an independent access path.

## Proposed follow-ups and order

1. **150-A: CT201 recovery/capacity qualification.** Fresh coherent backup,
   preserve/rebuild untagged metrics image, isolated restore without duplicate
   live identity/IP, dashboard/widget/metrics checks and core reservation.
   Smallest next task; no cutover is currently ready without these gates.
2. **150-B: separately approve CT201 relocation.** Review offline CT transfer
   versus backup/restore, downtime and disk mapping. One running instance with
   preserved identity/IP; prove service health and future backup coverage.
   Fence destination before source rollback; reconcile changed config/cache writes.
3. **150-C: qualify then move202.** PG17-compatible logical backup plus matching
   content/config/identity, isolated restore, auth/read/write/Git tests. Freeze
   writes for final transfer; rollback must account for new writes, not stale DB.
4. **150-D: printing window.** Fresh203 backup/config recovery, approved cable/
   printer destination and passthrough. Test real print; preserve reconnect rollback.
5. **150-E: DNS then edge in separate windows.**200 requires working independent
   admin/DNS path and resolver/filter/rewrites tests.204 requires identified tunnel/
   TLS recovery inputs and all internal/external routes verified. One active
   address/identity; fence destination before rollback. Keep original recovery points.
6. **150-F, parallel before retirement: Tailscale route responsibility.** Choose
   destination; review scoped route/ACL approvals and prove independent client
   access/failover. No route/identity/credential change is authorized here.
7. **150-G: separate physical retirement approval**, only after all accepted
   cutovers, no needed local payloads/guests, replacement remote access, verified
   backups and reviewed automation/cluster-removal consequences.

K3s/CSI remain unqualified for real-data moves. Interim core transfers do not wait
for them; future Kubernetes placement is a separate per-service decision. Existing
TrueNAS applications stay put. No Task110 repair or Task050 work performed.

## Node-removal gate

An infra shutdown without membership removal leaves3/4 votes, exactly current
quorum; another member loss would lose quorum. Reviewed removal leaving three
one-vote members should yield majority2; verify actual membership/votes/QDevice/
HA immediately before and after that future operation. Never lower expected
votes as an evacuation shortcut. Active HA daemons do not mean managed HA guests.

Before sale, prove no needed local volumes/snippets/backups or USB dependencies;
retain NFS/PBS access and DNS/tunnel/Tailscale paths, review Corosync/migration
network compatibility and remove only confirmed stale references. Prevent the
retired node reconnecting with old cluster identity. Configuration archival,
removal, credential cleanup and disk sanitization need approved procedures;
none is executed or authorized by this assessment.
