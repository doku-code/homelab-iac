# 110 - Three-server K3s bootstrap and controlled lifecycle

- Status: IN_PROGRESS / repository implementation; live install and lifecycle
  qualification not authorized or verified. Task100 accepted/DONE.
- Deliverable: pinned reproducible K3s/embedded-etcd installation and lifecycle
  on three distinct server VMs, including synthetic backup/restore evidence.
- Initial scope: design/code/tests only when assigned; live installation, token
  handling, network edits and fault tests require separate approvals.

## Required implementation decisions

Select supported pinned K3s/OS versions with verified release integrity and
documented upgrade path. No unpinned curl-to-shell. A small Ansible role owns
OS/config/binary/service and serial server lifecycle, not app Helm releases.
Use a separately approved ephemeral lab token, secret-safe delivery/no logs,
never a production Infisical identity. Persist matching token with approved
synthetic snapshots outside the disposable cluster. No sole key inside cluster.

Before bootstrap decide explicit non-overlapping pod/service CIDRs, private API
address/TLS SANs, peer ports, time/DNS, CNI and network-policy settings. Propose
baseline Flannel/CoreDNS; review bundled Traefik/ServiceLB ownership before120.
A documented single API address with alternate access is acceptable for A;
stable independently reachable API endpoint/failover is mandatory before B.
No Kubernetes API, etcd or SSH exposure to public ingress.

## Tests and observable acceptance

- Offline: role syntax and synthetic config rendering; exactly one initial
  cluster-init node, other servers join intended cluster; reject duplicate
  identity, mismatched critical settings and missing token; no secret in output.
- Live, after approval: three Ready server nodes and healthy etcd membership;
  intended TLS identities/network denials; second convergence leaves cluster
  stable and doesn't reset membership. Record versions and local etcd disks.
- Approved drills: lose one member, verify quorum/API, rejoin safely; two-member
  loss is unavailable, not falsely HA; restore a synthetic snapshot with matching
  token into isolated allocation and verify objects. Never run cluster-reset
  on existing production or copy a live member identity.
- Qualify serial upgrade/replacement procedure, drain/PDB behavior, snapshot,
  member removal and fencing; no blanket service restart or downgrade rollback.

Excludes Flux/apps, production secrets/data, TrueNAS changes, workstation host
roles and automatic destructive cleanup. On failure stop serial changes and
preserve healthy quorum; recover from reviewed compatible snapshot procedure.
Close with operator-accepted evidence; next120, no automatic Flux bootstrap.

## Repository implementation - 2026-09-26

Pinned profile, applied-output inventory validator, serial k3s_server role,
separate private-token/snapshot interfaces, fail-closed drift/state-loss checks,
offline CI tests and [lifecycle runbook](../docs/k3s-bootstrap.md) implemented.
No installation or real token generation. Official v1.35.8+k3s1 binary streamed
and SHA256 matched manifest/asset digest; no detached-signature claim.

Read-only: expected LAN routes/cgroupv2/no K3s directory on all three, no swap on
server-1, observed controller .119 and nftables command absent. Unknown VPN/site
ranges need operator confirmation. No baseline, enrollment, Terraform or network
changes repeated. Runtime firewall/ACL compatibility remains a live gate.

Acceptance tracking:

- Repository: synthetic shared settings/templates, duplicate identities, CIDR
  overlap, single init/order, private/missing token and snapshot/install approval
  tests; syntax and exact-SHA CI evidence reported at delivery.
- Live install: pending approval; three Ready servers, actual healthy etcd
  membership, CNI/DNS/TLS/denials and second convergence remain UNVERIFIED.
- Lifecycle: procedures prepared, not qualified. One-member failure/rejoin,
  controlled upgrade/replacement and isolated snapshot+token restore drills need
  separate approval and evidence before DONE. No reset/delete Make targets.
- Recovery: future snapshot, matching token, checksum/version, topology and
  Stage A authority recorded; no private export or kit/security redesign.

Stop after repository publication and CI/GitHub evidence; do not begin120.

Local checks: K3s synthetic render/guards and both playbook syntax checks PASS;
Stage A regression, 15 mocked VM cases (including unchanged workstation tests),
20 runner fixtures, two mocked logical-backup tests and ten synthetic kit tests
PASS. Configuration parser validates 59 YAML, 12 Python and 22 shell blocks.
These synthetic tests created no real cluster token, snapshot or live resources.
