# 150 - Priority pve-infra inventory and evacuation assessment

- Status: IN_PROGRESS; authorized read-only assessment recorded2026-09-28,
  pending operator review and scoped recovery/cutover approvals. No evacuation done.
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

## Read-only assessment - 2026-09-28

See [inventory and evacuation plan](../docs/pve-infra-evacuation.md) for evidence,
capacities, destinations, limits and proposed150-A through150-G follow-ups.
Strict SSH confirmed pve-infra/.10, AZW MINI S/N5095A, not pve-compute.
CT200-204 provide DNS, Homepage/custom metrics, Wiki.js/PG17, USB printing and
Caddy/Cloudflare. The host also supplies the observed primary Tailscale LAN route.
Four one-vote members/quorum3; no HA resources or replication observed.

Core capacity is plausible, not reserved/peak-tested. PBS includes200/202/204;
201/203 only have older snapshots, no current inclusion. No restore proof for
these five CTs. Cloudflare runtime source, tailnet failover, USB relocation,
custom metrics image recovery and complete consumer/automation review remain gaps.

Assessment criteria: identity/inventory/removal-impact observations gathered;
destinations/order proposed; operator review pending. Task150 remains open until
separately authorized migrations and node-removal prerequisites are accepted.
Within operator-managed evacuation maintenance, the smallest proposed scope is
150-A CT201 backup/image preservation/isolated restore and core reservation before
150-B relocation. This is not the project's next development task: follow the
canonical roadmap through110-A,120 and fresh125. Initial inventory is complete;
ordinary CT transfers do not replace declarative Kubernetes application work.
No live changes, DB/state inspection, secret-value retrieval or backup exports.
Task110 incident, Task050 and architecture refactoring were not started.
