---
title: "Homelab IaC - Canonical architecture"
status: "Operator direction reconciled; implementation and live gates remain separate"
updated: 2026-09-27
---

# Canonical Reconstruction Architecture

An experimental public IaC project for building and understanding a maintainable
homelab, not a production platform or an absolute-zero recovery system. Preserve
real data and credentials; reconstruct useful functionality, not old workarounds.
This is the single current design; recovery is a supporting capability.
[Roadmap](roadmap.md) owns sequencing; [tasks](../tasks/README.md) own acceptance.
Nothing here authorizes implementation, allocation, deployment or migration.

## Decisions and evidence

| Classification | Direction |
| --- | --- |
| APPROVED OPERATOR REQUIREMENTS | Proxmox virtualization; K3s preferred for suitable workloads; Flux initial GitOps candidate; Terraform infrastructure, Ansible OS/cluster bootstrap, GitOps Kubernetes applications, Infisical runtime secrets; node-local initial application data, future TrueNAS CSI |
| APPROVED OPERATOR REQUIREMENTS | A: three server VMs on pve-lab, NOT physical HA. C physical target: pve-k8s-01, pve-k8s-02, pve-core with one active voting K3s server VM each. B core/compute/lab is an optional superseded transition proposal, not a prerequisite |
| APPROVED OPERATOR REQUIREMENTS | Local system/etcd disks; initial stateful applications pinned to their local-data owner; TrueNAS CSI deferred until NAS readiness/qualification; no Longhorn/Ceph. Existing TrueNAS apps stay. Preserve workstation resources. Independent protected recovery material; no synced active state; external storage protection is operator-owned |
| APPROVED OPERATOR REQUIREMENTS | pve-lab is dedicated to experimental Kubernetes during transition; workstations remain powered off with configuration/state/mappings preserved. Initial proposal: 3 x 2-vCPU/4-GiB VMs, subject to measured host capacity |
| APPROVED DIRECTION | One stack definition, explicit input source, no mandatory Infisical or automatic fallback; Starter inputs versus Recovery inputs/data. Prioritize separately inventoried pve-infra evacuation, with core interim placement allowed |
| UNRESOLVED DECISIONS | Physical allocations/capacity/API failover, exact TrueNAS/CSI compatibility, ingress/Caddy placement, each service's DB/storage/backup and eventual shared backend; alternative input interfaces remain incomplete |
| IMPLEMENTED AND VERIFIED | Stage A VM/OS and minimum K3s baseline accepted after system-pod repair. Task120 Flux/source/disposable demo and one Git-driven update live verified; advanced drills remain open. CSI/service migration not implemented |

## Reconciliation and deployment contract - 2026-09-27

This operator-approved revision supersedes the earlier mandatory core/compute/lab
transition, undecided mini-PC hypervisor, permanent external Infisical placement
and recovery-first sequencing. It does not retroactively change dated audits or
claim their missing evidence. Recovery030 remains accepted historically; its
[dated scope reconciliation](recovery-contract.md#scope-reconciliation---2026-09-27)
preserves identity, integrity, credential protection and single-writer guarantees.

Deployment starts with supported Proxmox, network/time/SSH/API trust and admin
access, repository/tools and suitable persistent storage when needed. Installing
the first hypervisor or supporting arbitrary providers is outside current code.
Select a stack without unrelated homelab services. Exact current contracts and
portability gaps are in [deployment inputs](deployment-inputs.md); Stage A's thin
private/Infisical adapter is implemented and offline-tested in045, not live-qualified.
Other adapters remain planned. Normal Infisical, private input, Starter and Recovery
sources must feed the same Terraform roots/Ansible roles/GitOps definitions.
Source selection is explicit and missing values fail without logging secrets.

Fresh mode may initialize data only by explicit choice and with suitable storage.
Recovery/reattachment must reject missing or incompatible data/identity, never
silently initialize an empty DB. Execution order is infrastructure -> K3s ->
GitOps -> applications according to real dependencies, not permanent external
placement. Stages A/B/C describe physical topology, never credential phases.

### Actual baseline

Repository at c636d1f: eight Terraform roots, zero child modules, six local
state files; controller/example have no state. Fourteen Ansible playbooks,
nine roles, monitoring Compose and CI image source. No Kubernetes app definitions.
State presence/structure rechecked without printing attributes or private inputs.

Task 100 now adds a ninth root, `pve-lab-k3s`, and a shared headless VM module
plus an OS-only baseline. VMs303-305 are deployed and the Debian baseline is
live-verified on 2026-09-26. Stage A adds a seventh local
state authority. Existing roots remain unchanged. Recovery inventory/schema
follow-up and operator storage-protection scope clarification are recorded in
[Recovery Kit preparation](recovery-kit-preparation.md#stage-a-authority-update---2026-09-26),
without silently changing the accepted recovery contract.
See [Stage A workflow](k3s-stage-a.md) for inputs, tests and separate live gates.

Task100 is now operator-accepted/DONE. Task110's [K3s bootstrap](k3s-bootstrap.md)
is installed: one initial embedded-etcd server, serial
joins, private node API/manual fallback, Flannel/CoreDNS, disabled bundled
Traefik/ServiceLB/local-storage, scoped guest firewall and private lab-token path.
Operator reported second convergence with zero changes. In the preceding approved
maintenance, all three units/processes moved to0022, etcd remained healthy and
server-2 became leader (term3). Task110 records subsequent targeted system-pod
replacement and accepted minimum baseline; failure/restore/upgrade drills remain
unverified. Task120 now records live Flux/source/demo and Git-driven update
evidence. No wider architectural or physical-placement qualification is implied.

| Evidence | Known result | Limit |
| --- | --- | --- |
| Audit fd4435e, 2026-09-24 | Four Proxmox hosts; CT301 runner, CT300 PG candidate, CT209 Garage, VM207 Infisical, VM208 monitoring, DNS/proxy guests; Forgejo endpoint on TrueNAS | Historical, not complete current service/recovery proof |
| Code and previous qualifications | CT/runner/PG/Garage automation; PG disposable locking/crash/isolation/logical restore; Garage native Terraform locking rejected | No production backend or full host recovery qualified |
| Live quality CI | Operator-reported run139/01ccefb; directly observed run24/8c12871 and run25/c636d1f success; eight roots in latest workflow | Not deployment, recovery or runner isolation; Tasks010/020 security criteria unchanged |
| Earlier Task035 preflight, 2026-09-25 | pve-lab 32 threads/~30 GiB usable RAM, ~27.5 GiB available; workstations already stopped; local import/lab-vms capacity | Not concurrent peak capacity or permission to stop a workstation |
| Recovery preparation | GitHub independently matched c636d1f; synthetic manifest checks; PBS metadata and OCI digests inspected | No produced/decrypted kit, independently restored technical payloads or completed DR |
| Operator statements in this request | TrueNAS dedicated application SSD and 10 GbE uplink; mini-PC 8-to-16 GB intent | No measured latency/endurance, client bandwidth or future hardware deployment |

Task035 preflight remains intact: VMID603/.32 are unapproved proposals, DHCP
exclusion unknown; no plan/apply/start/convergence. It becomes an optional test
host for portable recovery, not a mandatory first guest. No new live inspection
was needed in this architecture review. Nextcloud/Plex/torrent actual layouts
and versions remain UNKNOWN. See immutable [audit](audits/2026-09-24/current-state.md)
and [recovery inventory](recovery-kit-preparation.md).

## Topology and sizing

```mermaid
flowchart TD
  X[Controller + code + explicitly supplied inputs] --> P[Existing Proxmox / local disks]
  P --> A[Stage A: three server VMs on pve-lab]
  A -. separate qualification and allocation .-> C[Stage C: k8s-01 + k8s-02 + core]
  A --> L[Explicit node-local application data]
  L --> W[Kubernetes stateful workloads]
  N[Future qualified TrueNAS CSI] -. progressive storage migration .-> W
  C -. later placement .-> W
  E[Required DNS / artifacts / workload inputs] --> W
```

| Stage | Proposal / budget | Failure domain and approval |
| --- | --- | --- |
| Historical current-layout evidence | Audited infra DNS/proxy, core infrastructure, compute runner/bots, lab workstations, TrueNAS/PBS | Not current pve-infra identity/inventory;150 must verify, never assume infra equals compute |
| A development | Three distinct headless Debian VMs, each 2 vCPU, 4 GiB RAM, 32 GiB local SSD-backed system/etcd disk; workloads on servers initially | Same physical host/power/storage. 12 GiB cluster from 32 GB physical, minus measured Proxmox overhead and safety headroom. Workstations remain off; no simultaneous workstation budget required |
| B optional historical transition | Core/compute/lab proposal retained for traceability only | Not on the critical path; no allocation or migration authorized |
| C physical target | One Proxmox VM each on pve-k8s-01, pve-k8s-02 and pve-core; all active control-plane/etcd voters | Mini-PCs jointly preferred for ordinary apps; core fallback and third voter, never offline standby. VM allocations depend on measurements and existing core reservations |

Operator-supplied hardware, not a new live inventory:

| Host | CPU / physical RAM | Local disk / networking |
| --- | --- | --- |
| pve-k8s-01 | BOSGAME E5 Plus, Ryzen3 5400U 4C/8T, 8GB DDR4 upgradeable | 256GB M.2 SATA SSD; two2.5GbE ports |
| pve-k8s-02 | Same profile | Same profile |
| pve-core | Origimagic N2 Pro, Ryzen7 6800H 8C/16T, 32GB DDR5 | 512GB NVMe; one integrated2.5GbE port; existing critical workloads reserved |

Use preferred node affinity, appropriate replica anti-affinity and measured
requests/limits, not mandatory mini-PC affinity or a custom scheduler. Do not
promise automatic move-back after recovery. Neither8GB host is assumed to run
all apps alone. Measure Proxmox overhead, guest memory and failover capacity;
ballooning is not capacity. No RAM/NIC purchase or live allocation decided here.

Budgets are proposals, not allocations or performance guarantees. Before A apply,
measure host use with workstations off; retain at least 2 GiB safety headroom
beyond Proxmox overhead. Do not modify workstations. If 4 GiB/node is insufficient, negotiate
capacity or placement first. Proposed scaling triggers: sustained host headroom
below 2 GiB, OOM, node MemoryPressure/DiskPressure, etcd fsync warnings or service
latency beyond its agreed budget => stop adding workloads and measure. Establish
24-hour representative workload baseline and one-node-loss capacity before
accepting physical placement for real workloads (not before its initial qualification).
Review storage below 20% free or inadequate restore/snapshot space. These are
not configured alerts or approved RPO/RTO/SLOs.

Upstream minimums do not include our application fleet. Three embedded-etcd
servers tolerate one member failure, not their shared host's failure.
[K3s requirements](https://docs.k3s.io/installation/requirements),
[etcd quorum](https://docs.k3s.io/datastore/ha-embedded).

## Ownership and interfaces

| Sole writer | Responsibility | Explicit boundary |
| --- | --- | --- |
| Terraform | Proxmox VM/disk/NIC lifecycle in per-environment roots | No app manifests, guest packages or etcd membership surgery; existing addresses/states unchanged |
| Ansible | OS/users/trust/time, pinned K3s config/binaries, controlled joins/upgrades/removals; initial Flux bootstrap | Hand off app objects to Flux; never continuously manage the same Helm release or app resource |
| Flux | Reviewed Kubernetes platform/application manifests and Helm releases from protected ref | No Proxmox state/credentials; one bootstrap root and explicit management hand-off |
| Operator input delivery / Infisical | Explicit source delivers variables; Infisical is normal operator source | No alternative implemented merely by documenting it; same roles/roots; DB/keys/bootstrap access independently available before Infisical recovery |
| TrueNAS administration | Pools/datasets/shares/quotas/encryption and storage guardrails | Later CSI owns delegated child volumes only, not objects simultaneously managed by Terraform/Ansible |
| Make/operator | Narrow operator commands and approval sequencing | No new orchestration framework or automatic adoption |

Adapt the tested headless primitive into a small reusable component for new
controller/cluster use. Task100 must not move workstation addresses. Environment
maps select node/identity/storage/network/sizing without copying a whole stack.
Use separate state for each environment. A node-variable change is NOT safe
etcd migration: it may replace the VM. Join/remove one member at a time with
quorum, fencing and snapshot checks, or explicitly rebuild a disposable cluster.
Never clone live etcd disks or start two copies of one member identity.

## Networking, ingress and trust

Recommend existing bridges initially only after approved IPs and pod/service
CIDR overlap checks against LAN/VPN/future sites. Flannel/CoreDNS/network-policy
baseline first, not a new CNI project. Private API; management sources restricted,
etcd only between servers, required CNI/node ports scoped to peers. Deny workload
access to management networks with tested policies and host/network controls;
namespaces alone are not isolation. No public API, etcd or DB endpoint.

A can use a documented server API address with a tested manual alternate. C
requires a stable independently reachable registration/API endpoint, TLS SANs
and failover test. VIP/LB mechanism remains a task110 decision, not an allocation.
Preserve current AdGuard/Caddy until individual availability decisions. The first
app uses port-forward/internal test access, not production DNS/ingress changes.

Recommend one pinned Flux-owned Traefik release when ingress is needed, after
disabling bundled Traefik on all servers. Explicitly decide ServiceLB ports and
ownership; avoid competing ingress writers/listeners. Caddy remains an edge
where justified, not a mandatory extra hop for every app. Review renewal,
certificate ownership and public routes separately. K3s includes ingress/LB
defaults: [networking services](https://docs.k3s.io/networking/networking-services).

Emergency access uses console/SSH and a protected address/fingerprint/CA map,
not disabled host/TLS verification. Public DNS/time/downloads or verified cache
must work without AdGuard. Reissue leaf certificates only after proving external
DNS/CA/account recovery; preserving every old leaf certificate is unnecessary.

## Storage and databases

### Initial development storage

The NAS is busy and not ready to own Kubernetes persistent application data.
It is NOT a prerequisite for fresh application development. Ownership remains
Terraform -> Proxmox VMs, Ansible -> hosts/K3s, Flux -> application manifests.
Use node-local data for initial stateful workloads where appropriate.

The inspected Stage A profile (`ansible/vars/k3s-stage-a.yml`) explicitly disables
K3s `local-storage`. Preserve that decision: the smallest initial pattern is an
explicit static Kubernetes local PV, a non-default `kubernetes.io/no-provisioner`
StorageClass with `WaitForFirstConsumer`, and a PVC. The PV must declare
`nodeAffinity` for one explicitly selected storage-owning node; workload placement
must respect that owner. Declare the directory, capacity, permissions and host
preparation through Ansible before Flux reconciles the PV/PVC and application.
Use `Retain` and explicit data cleanup/recovery ownership; a capacity declaration
alone is not a filesystem quota. No local volumes are implemented by this decision.

Loss/unavailability of that node makes its data and workload unavailable. The pod
must not fail over to a different node with empty or inaccessible data. Document
this limitation per workload, including backup/restore before any real-data move.
Keep the app consuming a PVC at a stable mount path; isolate PV, StorageClass
and placement declarations so later qualified CSI can replace them with an
explicit data migration and removal of local-only affinity, not an app redesign.
CSI portability still requires qualified attachment/fencing; it is not automatic HA.

Stateless applications should remain portable. Git/ConfigMaps/Secrets-backed
configuration does not justify a PVC merely because the old CT used a filesystem.
Homepage remains first, without persistence by default. Follow the
[concentric application pattern](roadmap.md#application-development-pattern).

### Future centralized storage

Task130 qualifies TrueNAS CSI when the NAS is ready, then suitable local workloads
can move progressively under separate data/cutover approval. For those workloads,
TrueNAS becomes an accepted single data-availability dependency. Its uplink does not
prove end-to-end latency, fsync safety or independent backups. K3s system disks
and etcd remain on local host storage. No Longhorn/Ceph in the initial target.
The official TrueNAS CSI is the preferred candidate, not installed or qualified.
Reported SCALE~25.10.7 must be verified live with official driver compatibility
before integration. Reported app SSD free space~100GB suggests only a preliminary
60-70GB app-data budget: no reservation, quota or volume authorized. Inspect actual
ZFS usage/headroom, snapshots, growth and single-disk risk first. No assumed
single-disk stripe expansion. Existing Plex/Nextcloud/other TrueNAS apps stay put.
Storage is a documented capability prerequisite, not hardcoded datasets for every
user. Compatible alternatives are design intent, not implemented/tested support.
The following NAS recommendations are future qualification guidance, not a gate
for the explicit node-local development pattern above.
Longhorn is only a possible measurement-driven future experiment; no task or
dedicated storage network is approved. Core's single NIC needs its own complete
network design if that future need arises.

| Workload | Recommendation | Hard gate |
| --- | --- | --- |
| NFS-compatible/shared files | TrueNAS datasets, explicit UID/GID/ACL, quotas/export clients | Multi-client permissions, disconnect/reconnect and restore; retain production data on claim deletion |
| SQLite | Single writer on filesystem over dedicated block volume, or native TrueNAS app; supported server DB alternative where useful | No shared NFS SQLite/WAL; prove old-writer fencing before remount on another node. RWO is not complete fencing proof |
| PostgreSQL/other client-server DB | Per-app DB native on TrueNAS where simplest; K8s DB only after qualified block storage/backup | Roles/version/transaction consistency and isolated restore; no automatic DB-on-NFS recommendation |
| Kubernetes block storage | Qualify maintained, installed-version-compatible TrueNAS CSI/iSCSI; static disposable volume first if compatibility unclear | Single attachment, stale attachment recovery, power loss, expansion, reclaim and backup. No production default StorageClass yet |
| Monitoring data | Bounded retention/resources; outside observer remains | Decide expendable metrics vs retained Grafana identity/config; cluster loss must remain observable |

[SQLite WAL](https://www.sqlite.org/wal.html) excludes network filesystems.
[TrueNAS CSI guidance](https://www.truenas.com/docs/solutions/integrations/csidriver/csidriver/)
covers NFS/block choices; installed version and compatibility remain unknown here.
No driver or storage credentials are provisioned. ZFS redundancy/snapshots are
not independent backups. DB and file/blob snapshots need a consistent boundary.

## Service reconstruction matrix

All placements are RECOMMENDATIONS, not migration authorization. The following
two tables together form each service's twelve-part reconstruction contract.
Current locations are dated evidence; versions/layouts not inspected stay unknown.
Every stateful migration requires a service-specific compatibility, recovery,
cutover and rollback task before any production writer changes.

| Service / desired functionality | Bootstrap role; proposed placement/declaration | Secrets, identity and irreplaceable data; storage/DB |
| --- | --- | --- |
| AdGuard: LAN DNS/filtering | Placement undecided from availability/dependencies; preserve current service, emergency DNS path required | Admin access, rewrites/filter policy/exceptions; local config; query history retention optional |
| Caddy: TLS edge/routes/remote access | Separate ingress/availability decision including external NAS services; no blanket outside/inside rule | DNS/tunnel credentials, account/CA material where irreplaceable, route policy; leaf certs reissuable with authority |
| Infisical: scoped runtime secrets | Valid future K8s app with independently supplied DB/keys/bootstrap inputs; no temporary Infisical required | Consistent DB + matching encryption keys; projects/policies/identities/secret versions; independent backup |
| Forgejo: Git/permissions/Actions/OCI | Not first recovery dependency. KEEP ON TRUENAS initially; declarative supported app/config rather than ad hoc runtime copy | DB/repos/app keys/Actions secrets/users/ACLs/registrations/package metadata+blobs; actual datasets unknown |
| Runner and OCI: trusted execution/artifacts | Preserve current role; eventual placement needs individual trust/availability review, not bootstrap-driven exclusion | Matching registrations/tokens and pull access; independently preserve OCI blobs/manifests or qualify external rebuild; no host workload secrets |
| Vaultwarden: vaults/accounts | Not sole break-glass store. DEFER UNTIL DEPENDENCIES QUALIFIED, then REBUILD IN KUBERNETES if storage safe | DB, attachments/sends, identities/encryption-related state; safe single-writer block or supported server DB, never replace vault with empty DB |
| Homepage: service navigation | No bootstrap requirement. REBUILD IN KUBERNETES after disposable demo; versioned config/manifests | Scoped widget secrets; config/customizations; normally no DB |
| Wiki.js: knowledge/documents | Not recovery source of record. REBUILD IN KUBERNETES after synthetic DB restore | DB/accounts/content/uploads/auth identities; dedicated logical DB + file dataset |
| Nextcloud: files/shares/collaboration | KEEP ON TRUENAS; not a migration target | Consistent DB/config/user-files, instance identity/salts/keys, ACLs and app compatibility; actual layout unknown |
| Plex: media/transcoding | KEEP ON TRUENAS; not a migration target | Library DB/metadata/account identity; media separate; GPU access/capacity to verify |
| qBittorrent/Gluetun: VPN-confined transfers | No bootstrap requirement. KEEP ON TRUENAS initially as scoped app/Compose workload | VPN credentials, session/resume/config and download files/permissions; confinement mandatory |
| Garage: internal object API if demanded | No bootstrap role. RETIRE IF NO LONGER REQUIRED, otherwise dedicated service pending consumer contract | Objects + metadata/layout/RPC identity; never Terraform state backend under rejected qualification |
| Monitoring: metrics/alerts/diagnostics | Outside observer supports recovery. ADAPT external observer + GitOps cluster collectors | Grafana identities/config, alerts/silences and selected history; bounded storage, no blind volume copy |
| Databases / CT300 tfstate | Per-service logical isolation; KEEP outside initially where simpler, conditional K8s DB later | Roles/grants/data/backup keys; CT300 remains candidate, zero production state; not Infisical DB or K3s etcd |
| D2 bots/workstations/compute | KEEP ON DEDICATED COMPUTE/HARDWARE; Terraform guest shape, Ansible capabilities | OS/license/auth/session/app/user state; CPU/GPU/USB/latency constraints; not automatic Kubernetes candidates |
| Print/peripherals | KEEP ON DEDICATED COMPUTE/HARDWARE until device contract established | Device/queue/config/access; no blanket retirement of unmodeled guests |

| Service | DNS/access; backup/restore and health acceptance | Cutover/rollback; discardable implementation |
| --- | --- | --- |
| AdGuard | LAN DNS; encrypted config recovery; forward/reverse/filter and internal-DNS-loss tests | Parallel resolver then reviewed client change, restore prior config; CT200/path incidental |
| Caddy | Approved edge routes only; protected config/accounts; TLS renewal + direct emergency tests | Test hostname then route switch/rollback; manual edits and needless proxy layers disposable |
| Infisical | Restricted TLS/admin access; DB+key restore; allowed/denied identity-scope tests | Freeze writes, restore isolated, switch/fence old writer; old VM shape/path incidental |
| Forgejo | HTTPS/SSH/Git/registry; coherent DB/repos/blobs backup; clone/push/ACL/package-pull tests | Freeze pushes/jobs/packages for final sync; one writer; rollback must include new writes/schema compatibility, not stale DB; current app mechanism changeable |
| Runner/OCI | Polling/scoped registry; encrypted identity and artifact catalogue; harmless job/pull/isolation tests | Stop original before matching identity starts; exactly one registration writer; legacy labels/CT300/caches not requirements |
| Vaultwarden | TLS/restricted admin; protected full data set; synthetic login/sync/attachment restore | Maintenance/final sync, one writer; rollback reconciles new vault writes; CT206/runtime incidental |
| Homepage | Internal HTTPS; config + secret recovery; widget/least-privilege tests | Parallel URL, route switch/config rollback; CT201 incidental |
| Wiki.js | TLS/auth; DB+files backup; edit/search/upload/restore tests | Read-only old source, final sync, one writer; schema-compatible reverse path; CT202/path incidental |
| Nextcloud | TLS/WebDAV/trusted proxies; DB/config/files consistent backup; file hashes/shares/permissions/jobs tests | Maintenance/final sync; retain immutable recovery point, reconcile writes before rollback; current version/runtime not automatically fixed |
| Plex | Restricted access; DB/config backup + independent media policy; playback/transcode/library tests | Isolated metadata test then one writer; prior version only with compatible DB; container details incidental |
| Torrent/VPN | Private UI, VPN-only egress; config/session backup; kill-switch/leak/restart tests | Pause transfer, coherent session handover, one instance; wrapper replaceable, confinement not |
| Garage | Private endpoints; object+metadata restore/API tests if kept | Inventory consumers before retirement; protect bytes/keys until accepted; CT209/backend experiment not reason to keep it |
| Monitoring | Internal UI/constrained scrape+alert egress; config/selected data backup; scrape/alert/cluster-loss tests | Parallel collection then deduplicated alert switch; old observer retained until acceptance; Compose topology not sacred |
| Databases | Private native TLS, no HTTP proxy; engine-native backup/isolated restore, role/transaction/lock tests | Fence old writer, require schema rollback compatibility; shared DB server/candidate sunk cost not a requirement |
| D2/compute/workstations | Restricted management; OS/app recovery sets; actual workload/peripheral acceptance | Own approved window, never stopped by cluster tasks; VM numbering incidental but current state identity protected |
| Print/peripherals | LAN-only access; queue/device recovery and real print test | Retain original until qualified replacement; Kubernetes rewrite not presumed beneficial |

First workload: public pinned stateless demo, zero production data/credentials.
Prefer maintained upstream charts when they meet a service contract; verify
support/version then, not an invented universal chart migration.

## Availability and recovery

| Failure | Automatic behavior / accepted outage | Manual recovery and required proof |
| --- | --- | --- |
| One server VM | Two members retain quorum; stateless replicas can reschedule only with capacity/placement | Test API/endpoint and rescheduling; local data/block fencing may prevent automatic recovery |
| One physical host | A loses all cluster nodes; B/C can retain quorum with one server lost | Approved member rebuild and fencing; surviving workload/storage/network capacity separately proven |
| TrueNAS unavailable | Dependent apps/DBs unavailable by accepted design; local etcd/API may remain | Restore storage and consistency before app writes; no forced duplicate DB writer; Forgejo on NAS also affected |
| DB outage/corruption | App outage; restarting a pod is not data repair | Freeze, isolated compatible restore, verify roles/data, approve promotion; RPO/RTO measured later |
| Forgejo/registry down | Existing workloads may run; reconcile/new pulls/builds may fail | External source and artifacts; explicit reviewed source recovery, no automatic untrusted upstream failover |
| Infisical down | Cached/materialized secrets may survive; expiry/new startup/rotation may fail | External DB+key recovery, narrow independent bootstrap access; no guaranteed availability from cache |
| Complete K3s loss | No automatic recovery claimed | Independent controller: reconstruct nodes; snapshot+matching token OR fresh GitOps rebuild plus service restores, with identity requirements decided |
| Controller/whole homelab lost | Complete recovery NOT VERIFIED | Independent Mac/Linux, code, protected material/access supplied by operator and documented foundation prerequisites; chosen offline path must be tested before claimed |

Recommend native reproducible tools on Mac ARM64/Linux AMD64, optional disposable
VM adapter. A Forgejo-only recovery container image would recreate the bootstrap
cycle, so it cannot be mandatory. Reuse pins/requirements and small Make interfaces,
not a new recovery OS or orchestration product.

Order: controller/code/explicit inputs -> documented hypervisor/network/trust/
local-storage prerequisites -> infrastructure -> K3s bootstrap or restore -> Flux
from reviewed accessible code -> apps with suitable storage and explicitly fresh
or restored DB/files/identity. Recover NAS/PBS or artifacts first only when a
selected service needs them. Neither Infisical nor Forgejo must run merely to
obtain supplied inputs. Explicitly return one state/data writer. Disposable K3s can use public artifacts
and isolated test tokens without production secrets or a full production kit.

Separate: small protected kit (authority map/private inputs/break-glass/trust/
access references/technical-backup receipts); service backup sets; bulk personal/media
backups; public rebuild code/artifacts. Required independent bytes must actually
exist, not only a PBS pointer. A preserved K3s snapshot also needs its matching
server token; protect both as sensitive material, outside failed cluster custody.
[K3s backup/restore](https://docs.k3s.io/datastore/backup-restore).
If encrypted, the archive's sole decryption method must remain outside it.

[Recovery contract](recovery-contract.md) authority/integrity rules remain valid;
its dated reconciliation supersedes project-owned storage/account custody gates.
Adapt the hardcoded six-root verifier before capturing new states; its structural
PASS does not prove complete catalogue or Git bundle validity. Synthetic tooling
first; real export/decryption/drill separately approved. No plaintext synced
staging, no production kit on test VMs by default.

## Priority pve-infra evacuation

The operator intends to sell pve-infra. [Task150](../tasks/150-pve-infra-evacuation.md)
completed its initial authorized read-only inventory; see the dated
[assessment](pve-infra-evacuation.md). It is not pve-compute. Ordinary CT transfers
to core are operator-managed maintenance, independent of the concentric
application-development sequence in the roadmap. Preserve per-service capacity,
recovery and approval gates, plus DNS, Tailscale and quorum retirement requirements.
No service or node is stopped, migrated or retired by this planning update.
Check cluster quorum, shared storage/network and PBS effects before proposing
decommission. Keep historical resources and data until accepted cutover.

The approved replacement route design is now [150-F](../tasks/150-f-tailscale-routers.md):
two independent unprivileged Debian LXCs on pve-k8s-01/02, in the EXISTING tailnet,
both advertising 192.168.0.0/24 with native Tailscale failover. Separate identities,
no cloned state, VIP or host networking changes. Repository preparation is not
live deployment or failover proof; pve-infra's service remains unchanged.

## Backend and ownership transitions

Recommend local state and one designated operator writer initially, with protected
independent captures. It does not coordinate separate controllers/copies; no CI
applies or automatic stale fallback. [Terraform local locking](https://developer.hashicorp.com/terraform/language/backend/local).
Before multi-writer/protected infrastructure CD, Task080 evaluates requirements.
External PostgreSQL is a leading conditional option due to existing evidence,
not sunk cost: verify-full/identities/network/full recovery remain gaps. Consul
adds another quorum service without established need; defer unless a concrete
requirement justifies it. Garage remains rejected. Never host bootstrap state
inside the cluster it must recover. No backend selection/migration occurs here.

Ownership transition: privately inventory address/lineage, freeze all writers,
verify recovery set, review mapping/import/state move only if necessary, approve
no-unexpected-replacement plan, transfer once and fence previous writer. No root
refactor combined with backend migration. New nodes use new state without adopting
old guests. App transitions use isolated target/coherent restore/single-writer
cutover; keep old resource and rollback point until acceptance. Never blindly
destroy existing resources or run duplicate DB/runner identities.

## Existing work disposition

| Workstream | Classification | Reason / successor |
| --- | --- | --- |
| Existing roots and local authorities | KEEP | Real ownership protected; no cleanup of addresses/states in planning |
| Headless VM primitive | ADAPT | Tested base for three new nodes; Task100, no workstation moves |
| Dedicated controller035 | ADAPT, optional/deferred | Portable050 primary; proposed VM603/.32 remains unapproved |
| Controller deps/guest Ansible | KEEP / ADAPT | Reuse tools/OS ownership, add K3s lifecycle; no workstation host role on cluster nodes |
| Mandatory LXC-first090 | RETIRE as roadmap prerequisite | No demonstrated second LXC use case; active CT code stays |
| Recovery contract030 | KEEP | Independent custody and single authority still required |
| Kit040 tooling | ADAPT | Separate portable synthetic checks from production completeness, evolve inventory deliberately |
| Independent controller050 | ADAPT | Mac/Linux first; full kit and VM not prerequisite for synthetic implementation |
| Mandatory PG/Consul060/070 sequence | REPLACE | Requirements-led080; no forced Consul deployment |
| Forgejo quality CI | KEEP | Working checks; expand only for new code, never grant deployment privileges |
| Shared runner trust | ADAPT | 010 unresolved; no production cluster-admin or state credentials on shared quality path |
| Infisical authority | KEEP / ADAPT | Preserve runtime authority; explicit bootstrap and Kubernetes sync scope |
| Monitoring Compose | ADAPT | Keep external observation; cluster collectors by need; exporter/Compose coupling deferred |
| Existing services | UNDECIDED per service until qualification | Preserve required function/data, not every legacy deployment |
| Garage backend direction | RETIRE | Failed locking; object service continuation needs a real consumer |

## Operator decisions before implementation

Task100's approved apply/start and guest baseline are complete; further live
actions are not authorized by this document. Task110 incident remains open; storage/fencing
before stateful tests; payload/custody before migrations; B/C capacity/member
transition before live relocation; backend and runner security before privileged CD.

Flux reads reviewed code; generic bootstrap writes manifests to Git and needs
an explicit ownership/credential hand-off, not silent invocation.
[Flux installation](https://fluxcd.io/flux/installation/).
Quality CI must never receive production kubeconfig, state or Infisical credentials.
