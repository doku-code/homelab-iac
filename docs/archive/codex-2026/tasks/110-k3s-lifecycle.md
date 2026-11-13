# 110 - Three-server K3s bootstrap and controlled lifecycle

- Status: IN_PROGRESS; minimum usable baseline A live verified and operator
  accepted2026-09-28. System pods recovered through approved targeted
  replacement. Advanced lifecycle B remains unverified; full task is not DONE.
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

## Acceptance A - Minimum usable development foundation

This gate, not completion of the advanced drills below, releases Task120.
Record explicit operator acceptance of A; Task110 remains open for B.

- Offline: role syntax and synthetic config rendering; exactly one initial
  cluster-init node, other servers join intended cluster; reject duplicate
  identity, mismatched critical settings and missing token; no secret in output.
- Live, after approval: three Ready server nodes and healthy etcd membership;
  intended TLS identities/network denials; second convergence leaves cluster
  stable and doesn't reset membership. Record versions and local etcd disks.
- Healthy CoreDNS and metrics-server, functional cross-node pod networking and
  service DNS, working private API and stable repeatable Ansible configuration.
  Projected-token failure repaired and minimum functional checks passed2026-09-28;
  see evidence below. No advanced drill is implied by this qualification.

## Acceptance B - Advanced lifecycle qualification

Planned, separately approved work; not a prerequisite for disposable Flux or
fresh applications after A. Preserve procedures and evidence; no drill is waived
or considered passed by this sequencing change.

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

Sequencing clarification 2026-09-28: full DONE requires A and B; Task120 may
start after A acceptance without waiting for B. The next single implementation
scope is the projected-token incident and A qualification, beginning with
separately approved metadata-only diagnosis; no repair is authorized here.

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

## Operator administration source correction - 2026-09-26

Operator confirms wired DHCP reservation 192.168.0.90; k3s_admin_cidrs now contains
only 192.168.0.90/32, replacing the incidental earlier .119 observation. No current
Mac address prerequisite added: Ansible uses SSH, unchanged by the API firewall,
and Kubernetes health checks execute on guests. Tests cover the exact rendered
allowlist, no LAN-wide grant, untouched SSH and guest-local health checks.
No shared Forgejo runner allowlisting or cluster-admin credential delivery;
dedicated administration/protected deployment remain separate future work.

Read-only Mac netstat/route checks: active LAN 192.168.0.0/24, no overlapping
non-default IPv4 routes for 10.42.0.0/16 or 10.43.0.0/16. Both use gateway .1
on en0. scutil reports Tailscale and ProtonVPN disconnected; inactive VPN/site
routes remain unverified. No VPN activation, guest changes or real token creation.
Correction checks PASS: k3s-check, Stage A regression, configuration/script
parsing and git diff --check. No live firewall behavior claimed by rendering.
Previous implementation passed Forgejo run32/API143 at 0f89723; correction's exact
CI/GitHub result is reported at delivery. Task110 remains open for live acceptance.

## Umask correction and read-only preflight - 2026-09-27

Operator reports successful install and second convergence changed=0/failed=0/
unreachable=0 on all three. Earlier pending-install statements above are dated
implementation evidence, superseded by this report, not proof of full health.
Observed CoreDNS StartError128 (/coredns permission denied) and metrics-server
exit2 (/tmp permission denied), both server-1, block qualification. All service
units use0077; server-1 K3s/containerd inherit it and snapshot roots are0700.

Template corrected to0022 with regression assertions for explicit0700/0600
private paths, no_log/diff suppression and unchanged normal drift rejection.
No live unit applied, process restarted or filesystem remediated. The
[unit-only maintenance proposal](../docs/k3s-bootstrap.md#umask-incident-proposed-maintenance-not-executed)
requires separate approval, all-member health gates and server-1 API fallback.

Actual etcd inspection: all three local health endpoints true; authenticated
member/status/alarm queries agree on three voting members, cluster ID,
leader server-1, term2, etcd3.6.14 and no alarms. Applied index equals Raft index
on each endpoint. No datastore contents or credentials exported. This verifies
current etcd health, not interruption/restore safety. Snapshot0700 persistence
remains a post-restart observation gate, not permission for recursive repair.
Task110 stays open; broader architecture amendment and Task120 remain pending.

## Subsequent maintenance evidence and architecture handoff - 2026-09-27

The preceding explicitly approved live operation (not this documentation session)
applied only0077->0022 in order server-2, server-3, server-1 with exact unit-diff
guard. All-member actual etcd gates passed before/after each restart, no alarms
or applied-index lag. All nodes/API Ready, K3s AND containerd processes0022.
API fallback through server-2 returned ok during server-1 restart; leader then
server-2, term3, same member identities. No storage remediation/pod deletion.

Both pods advanced beyond /coredns and /tmp errors but remain CrashLoopBackOff
on projected service-account token permission denied (165 restarts observed).
STOPPED as required. Next incident step: separately authorized metadata-only
volume path/mode/ownership diagnosis; no reading token bytes or implied chmod.
Task110 qualification, lifecycle drills and operator acceptance remain open.
Broader architecture is now reconciled in the canonical architecture/roadmap;
that approval does not authorize incident repair, Flux or live inspection here.

## Approved pod repair and usable baseline qualification - 2026-09-28

Targeted diagnosis found surviving sandbox shims from26 September with0077,
although K3s/containerd on all three guests used0022. Both container upper layers
had root-owned0700 /var/run/secrets and kubernetes.io ancestors. CoreDNS UID65532
and metrics-server UID1000 could not traverse them. Projected token metadata was
already appropriate (0644/root and0600/UID1000 respectively); no token bytes read.

Before intervention: all nodes Ready; each actual etcd endpoint healthy; identical
three voting members/cluster identity, leader server-2, term3, no alarms and
applied index equal to Raft index at each endpoint. Pod -> ReplicaSet -> Deployment
ownership verified; both old pods still CrashLoopBackOff (486/487 restarts).

Only normal pod deletion was performed, CoreDNS first. Its replacement became
Ready and answered kubernetes.default.svc.cluster.local via both10.43.0.10 and
its pod IP before metrics-server was touched. No Deployment/ReplicaSet edits.

| Component | Old pod / UID | Replacement / UID | Runtime evidence |
| --- | --- | --- | --- |
| CoreDNS | coredns-c5fdd76cf-2vj74 / f061eee8-3719-4f9d-938b-771de7b09fc2 | coredns-c5fdd76cf-g2fhd /49e4ff8a-b621-49b0-87de-2dd201154e00 | server-2,10.42.1.2; new sandbox5d4d325dd3f0, shim127315 actual0022; Ready, zero restarts |
| metrics-server | metrics-server-7f4b6d9bd7-dpb78 /e5ea9846-a1fa-4fb5-a49f-8b4d749c1856 | metrics-server-7f4b6d9bd7-z2bpw /b2ef1dde-fa2a-416b-ac0c-315333d37796 | server-3,10.42.2.2; new sandbox709dc95dd658, shim127313 actual0022; Ready, zero restarts |

Actual running process-root metadata: both secrets ancestors0755/root, mounted
serviceaccount1777 and ..data0755. Token modes/owners unchanged and contents never
opened. Metrics API returned fresh measurements for all three nodes.

Functional qualification used namespace task110-qualification-20260928, confirmed
absent before creation: three node-bound non-root pods, no service-account token,
read-only rootfs, dropped capabilities, bounded resources and300s deadline; one
ClusterIP Service and disposable emptyDir data. BusyBox1.37.0 resolved to
sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e.
All six directed cross-node HTTP paths passed. Every pod resolved Kubernetes
service DNS and the test service FQDN, then fetched the test service successfully.
Only that test namespace/resources were deleted; absence verified afterward.

Post-checks: three actual etcd endpoints still healthy, same voters/leader/term,
no alarms, applied=Raft on each; local /readyz returned ok on all three APIs.
Both system pods remained1/1 Ready with zero restarts. Owned nftables tables on
all guests retained scoped API/etcd/kubelet/VXLAN rules and operator .90 allowlist.
This is rule inspection, not a new exhaustive negative-source firewall test.
Earlier operator-reported Ansible convergence changed=0/failed=0/unreachable=0
is retained as dated evidence; no new convergence or installation was run.
Existing synthetic K3s regression passed outside the controller sandbox after
the sandboxed attempt could not start Ansible's local RPC process. No code changed.

Minimum usable Stage A was accepted by the operator for the disposable Flux
milestone on2026-09-28; Flux was not part of this qualification. Full110 stays open: member-loss,
rejoin, controlled upgrade and isolated snapshot/token restoration are unperformed.
No K3s restart, shim kill, forced deletion, chmod, etcd mutation, image purge,
infrastructure change, service migration or secret export was performed.
