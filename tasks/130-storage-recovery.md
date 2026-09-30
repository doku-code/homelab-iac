# 130 - TrueNAS storage and synthetic stateful recovery

- Status: DEFERRED until the NAS is ready and this milestone is separately assigned,
  after110 acceptance A/120 and verified TrueNAS version/storage access.
- Deliverable: evidence-based NFS/block/database patterns, not a universal DB move.
- Scope: compatibility/inventory and code first; approve dedicated throwaway
  datasets/volumes/scoped credentials and isolated outage drills separately.

Initial stateful app development uses the explicit
[node-local contract](../docs/architecture.md#initial-development-storage), not
this milestone as a prerequisite. Later qualify CSI and progressively migrate
suitable workloads, with explicit data transfer, placement and recovery review.

Start with the smallest applicable CSI/protocol, permission, persistence and
recovery qualification for that workload; Wiki.js is an early candidate. Unused
protocols and broader drills remain explicitly unverified follow-ups, not gates
for stateless apps. Real-data cutover still requires every applicable consistency,
fencing and independent restore criterion below; synthetic success is not migration.

Read-only inventory must establish actual TrueNAS release, app SSD capacity,
datasets/ACLs, protocol support, network path and independently recoverable backups.
Reported SCALE~25.10.7 and ~100GB app-pool free space are operator estimates,
not verified inventory. Initial60-70GB app-data budget is provisional, not a
quota or allocation. Check ZFS headroom, retention, growth and single-disk risk;
no assumed single-disk stripe expansion. Official TrueNAS CSI is the preferred
candidate: verify exact live version and official feature/security compatibility
before implementation. Static synthetic volumes are
acceptable for initial protocol tests. No Longhorn/Ceph, production default class,
NAS-wide reboot or backup schedule changes. Node system/etcd remain local.
Existing Plex/Nextcloud/other TrueNAS apps are not migration targets. Define
storage capabilities and configurable endpoints, not a universal NAS provisioner.
Compatible alternative providers remain unimplemented until separately tested.
Absent qualified NAS storage blocks NAS-backed deployment, not suitable node-local
stateful development. Local-node loss has no automatic data failover.
Central NAS outage remains an accepted dependency, not end-to-end storage HA.

Test NFS-compatible files: UID/GID/ACL and multi-client access, checksums,
disconnect/reconnect, snapshot versus independent restore. Test block for DB:
single writer, forced-disconnect fencing/stale attachment behavior, filesystem
and transaction consistency, expansion and retained data after PVC deletion.
Do not infer fencing from RWO alone. No SQLite WAL on NFS; use qualified block,
native TrueNAS or supported client-server DB as the service contract requires.

Using synthetic PostgreSQL/SQLite as appropriate, test engine-native backup,
isolated restore, roles and transactions. Show what happens when storage or DB
is down; app rescheduling is not consistency/recovery proof. Record accepted
outage, measured recovery interval and data loss, without inventing RPO/RTO.

Acceptance: offline configs/tests plus live bounded protocol, fencing, negative
permissions and isolated restore evidence accepted; declarative configuration,
secret references, payload backup and retained ownership clearly separated.
Cleanup deletes only explicitly listed disposable datasets after approval; no
production PVC deletion. Next140 placement or individual service contract.
