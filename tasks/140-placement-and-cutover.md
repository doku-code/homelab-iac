# 140 - Distributed placement, permanent hardware and service reconstruction

- Status: PLANNED epic; split each section into a scoped execution task before work.
- Initial permission: planning/read-only only when assigned, never implicit migration.
- Dependencies/acceptance per substage in [roadmap](../docs/roadmap.md).

## A - Optional historical Stage B transition

The core/compute/lab proposal is retained by ID for traceability, superseded as
a mandatory step on2026-09-27. Do not deploy it without separate justification
and approval. It is not a dependency of B,120 or pve-infra evacuation.

## B - Permanent mini-PC placement

After110 acceptance and actual hardware/capacity/trust checks, qualify one Proxmox
server VM each on pve-k8s-01, pve-k8s-02 and pve-core. All are active voting etcd
members; core is not standby. Use the [canonical hardware contract](../docs/architecture.md#topology-and-sizing).
No mandatory140-A,130/full040 prerequisite or RAM upgrade; measure8GB hosts and
existing core reservations. Local system/etcd disks only. New allocations and
member transitions require separate approval; never simultaneous replacement.
Require API failover, healthy quorum and node maintenance;120/130 later add
representative workload/storage evidence before real-workload acceptance.
Preferred mini-PC affinity must allow core fallback; no automatic move-back or
assumption one mini can run everything. Accept the placement before retiring
old members. Physical migration is not merely
a state edit or restoring VM snapshots into an active etcd cluster.

## C - One service per reconstruction/cutover task

Use [architecture service matrix](../docs/architecture.md#service-reconstruction-matrix).
Before irreplaceable-data cutover: qualify required independent material (reuse
040/050, not blanket completion of a full recovery program), qualify
target placement/storage, service version/schema compatibility, consistent
DB/files/identity backup and isolated restore, health/ACL/function tests and
measured recovery. No bulk personal data stuffed into the small kit.

Approve each final write freeze, snapshot/export, endpoint switch and rollback
window. Fence old writer; preserve post-cutover writes and migration compatibility
before rollback. Retain old guests/authority until accepted; separate approved
decommission task, never blanket Terraform destroy. New implementation may use
different runtime/version/path but cannot silently lose identities or data.

Service recovery must demonstrate trusted independent controller -> documented foundations ->
cluster restore/rebuild -> GitOps -> consistent service restores without relying
on failed internal services. Test loss of cluster and unavailable TrueNAS/Forgejo/
Infisical with scoped synthetic/isolated exercises before risky production drills.
Keep actual backup bytes and decryption paths independent. No claim of physical
host recovery from a VM hosted on that same host.

Next: separately assign next service or080 backend/CD gate. This epic has no
single blanket apply approval and cannot be DONE from one successful demo.

[150](150-pve-infra-evacuation.md) is a high-priority parallel inventory/cutover
track, including interim core placement without waiting for this entire epic.
Existing TrueNAS apps are excluded from migration. Service placement remains
open until accurate inventory, functional and availability review.
