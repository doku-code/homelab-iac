# 140 - Distributed placement, permanent hardware and service reconstruction

- Status: PLANNED epic; split each section into a scoped execution task before work.
- Initial permission: planning/read-only only when assigned, never implicit migration.
- Dependencies/acceptance per substage in [roadmap](../docs/roadmap.md).

## A - Distributed current hardware

After120 measurements and130 storage failure qualification, measure core/compute/
lab capacity under representative critical/bot/workstation load. Propose one
server per host with survivor workload capacity and stable private API endpoint.
No workloads displaced to fit. Approve allocations and exact plans separately.
Qualify member-by-member replacement with healthy quorum/snapshot/token/fencing
or deliberate disposable rebuild, not a blind node-variable apply. Demonstrate
physical-domain loss and maintenance without claiming TrueNAS HA. Stop on quorum
risk, retain old recovery points and never start duplicate members.

## B - Permanent mini-PC placement

After actual hardware and A evidence, decide Proxmox+VM versus bare metal using
8-GB measurements and host reserve. Support16-GB upgrade through sizing profile;
no32-GB purchase dependency. New host installation/trust/storage and member
transition separately approved. Prove one-node maintenance/failure and capacity;
bare metal requires its own non-Proxmox install/recovery interface. Accept the
new placement before retiring any old member. Physical migration is not merely
a state edit or restoring VM snapshots into an active etcd cluster.

## C - One service per reconstruction/cutover task

Use [architecture service matrix](../docs/architecture.md#service-reconstruction-matrix).
Before production: complete040/050 for required independent material, qualify
target placement/storage, service version/schema compatibility, consistent
DB/files/identity backup and isolated restore, health/ACL/function tests and
measured recovery. No bulk personal data stuffed into the small kit.

Approve each final write freeze, snapshot/export, endpoint switch and rollback
window. Fence old writer; preserve post-cutover writes and migration compatibility
before rollback. Retain old guests/authority until accepted; separate approved
decommission task, never blanket Terraform destroy. New implementation may use
different runtime/version/path but cannot silently lose identities or data.

Production DR must demonstrate fresh independent controller -> foundations ->
cluster restore/rebuild -> GitOps -> consistent service restores without relying
on failed internal services. Test loss of cluster and unavailable TrueNAS/Forgejo/
Infisical with scoped synthetic/isolated exercises before risky production drills.
Keep actual backup bytes and decryption paths independent. No claim of physical
host recovery from a VM hosted on that same host.

Next: separately assign next service or080 backend/CD gate. This epic has no
single blanket apply approval and cannot be DONE from one successful demo.
