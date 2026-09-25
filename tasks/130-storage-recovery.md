# 130 - TrueNAS storage and synthetic stateful recovery

- Status: PLANNED after110/120 and verified TrueNAS version/storage access.
- Deliverable: evidence-based NFS/block/database patterns, not a universal DB move.
- Scope: compatibility/inventory and code first; approve dedicated throwaway
  datasets/volumes/scoped credentials and isolated outage drills separately.

Read-only inventory must establish actual TrueNAS release, app SSD capacity,
datasets/ACLs, protocol support, network path and independently recoverable backups.
Choose maintained compatible CSI only after this; static synthetic volumes are
acceptable for initial protocol tests. No Longhorn/Ceph, production default class,
NAS-wide reboot or backup schedule changes. Node system/etcd remain local.

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
