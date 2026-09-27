# 150 - Priority pve-infra inventory and evacuation assessment

- Status: PLANNED / high priority parallel track; live inspection not authorized.
- Dependencies: explicit node identity/access approval, not full K3s/CSI/kit work.
- Scope: first targeted read-only inventory, then separately assigned cutovers.

Do not equate pve-infra with pve-compute. Establish physical identity, cluster
membership/votes, guests, disks/storage dependencies, bridges/routes/DNS, backup
coverage and restore evidence. Determine Proxmox quorum/removal consequences,
shared storage/network/PBS dependencies and consumers before proposing removal.
Historical inventory is a lead, not proof of live identity or service placement.

For each actual service record function, identity/data, upstream/downstream
dependencies, capacity, backup/restore, destination and rollback. Choose qualified
Kubernetes, interim/permanent pve-core, or justified external placement. Keep
core's critical workload reservations. Do not wait for every K8s milestone to
prepare an independently safe interim move. Existing TrueNAS apps stay untouched.

Acceptance for assessment: operator-reviewed actual inventory; complete per-service
destination/remaining evidence; infrastructure removal-impact analysis; prioritized
bounded cutover tasks with backups, single-writer switch and rollback gates.
Assessment is not evacuation completion. DONE requires separately authorized
migrations accepted and all node-removal prerequisites verified. No stop/delete/
migrate/decommission, cluster-membership change or live inspection in this task
until explicitly authorized. Retain old services and recovery points until accepted.
