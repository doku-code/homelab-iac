# Stage A K3s bootstrap and lifecycle

[Task110](../tasks/110-k3s-lifecycle.md) is installed; the operator reports a
second convergence with changed=0, failed=0 and unreachable=0 on every server.
Live qualification is blocked by the container permission incident below.
Task100 is operator-accepted. Lifecycle/recovery drills remain unverified.
Three servers on one pve-lab host are **not physical HA**.

## Installed profile

Authoritative shared settings: `ansible/vars/k3s-stage-a.yml`. Identities/IPs
come only from Stage A's applied `ansible_inventory`, not another host list.
`scripts/k3s-lab.py` validates and combines them into temporary JSON inventory;
strict SSH checking is mandatory, enrollment is not repeated.

| Setting | Proposed value |
| --- | --- |
| Release | `v1.35.8+k3s1`, stable Kubernetes 1.35 maintenance line |
| AMD64 SHA256 | `12f81c9bb5b71e098a4f7a2d187e350902a9339a6c3d5e56c20a03f7a417e07f` |
| Join order | server-1/VM303/.33 initializes embedded etcd; server-2/VM304/.34, then server-3/VM305/.35 join |
| Private API | `https://192.168.0.33:6443`; each server binds its private node IP |
| TLS SANs | All three node IPs and allocated hostnames; SAN security enabled; no external DNS/LB |
| Pods / services / DNS | `10.42.0.0/16` / `10.43.0.0/16` / `10.43.0.10`; cluster.local |
| Networking | Flannel VXLAN on eth0, CoreDNS, kube-proxy and network-policy controller enabled |
| Bundled components | Traefik, ServiceLB and local-storage disabled everywhere; metrics-server and Helm controller retained; no Flux/apps |
| Storage | Local `/var/lib/rancher/k3s`, including etcd; no NAS system disks, CSI, Longhorn or Ceph |
| Credentials | Dedicated disposable lab server token; root-only token/kubeconfig; secrets encryption enabled |
| Local snapshots | Every 12 hours, retention 5, `/var/lib/rancher/k3s/server/db/snapshots`; not independent recovery |

Release evidence 2026-09-26: official non-prerelease, published 2026-08-27.
Streamed binary SHA256 matched the official
[AMD64 manifest](https://github.com/k3s-io/k3s/releases/download/v1.35.8%2Bk3s1/sha256sum-amd64.txt)
and GitHub asset digest. Binary not executed/installed/retained. This verifies
HTTPS/checksums, not a detached signature. See
[release notes](https://docs.k3s.io/release-notes/v1.35.X) and
[supported Kubernetes versions](https://kubernetes.io/releases/); recheck support
and advisories before delayed installation or upgrade.

Read-only guest checks: only LAN192.168.0.0/24 and default routes, cgroupv2, no
existing K3s directory on all three; no swap listed on server-1. Installation
checks all three. Proposed CIDRs do not overlap the observed LAN or each other.
Read-only Mac route check on 2026-09-26: no active non-default IPv4 route
overlaps either CIDR. Both 10.42.0.1 and 10.43.0.1 resolve through the normal
default gateway 192.168.0.1 on en0. Tailscale and ProtonVPN report disconnected;
their inactive routes were NOT checked. Unknown VPN/site ranges still require
confirmation before connecting those networks. No routes/network settings changed.

## Network boundary and API fallback

Role installs iptables/nftables/conntrack/socat, enables overlay/br_netfilter and
IPv4 bridge forwarding. Own nftables INPUT table permits:

- TCP6443: peers, pods and operator's reserved wired Mac address `192.168.0.90/32`.
- TCP2379-2380 and UDP8472: peer IPs only.
- TCP10250: peers and pod CIDR for metrics-server.
- Loopback allowed; other sources (including IPv6) dropped on these ports.

SSH/unrelated rules untouched; no global ruleset flush. K3s requires the scoped
firewall service. This is not general LAN isolation or default-deny pod egress:
Task120 must prove workload-to-management denials before untrusted workloads.
No NodePort/ingress/public routes created. Proxmox ACLs must allow peer traffic;
guest rules cannot override upstream denial. Actual nftables syntax/behavior and
denied-source tests remain live gates. The earlier observed .119 was not the
administration reservation. Mac Wi-Fi may use another IP: SSH remains unaffected
by this API allowlist, and bootstrap health checks run on each guest against its
own API address. The Mac need not currently have .90 to run Ansible. Direct Mac
API access requires the approved .90 source; do not widen access to the LAN.
The shared Forgejo quality runner is not an administrator and receives no
cluster-admin credentials. Dedicated administration/protected deployment are
separate future work, not bootstrap prerequisites. Do not blindly reload the
additive firewall.

Manual fallback: use `.34:6443` or `.35:6443` with the same cluster CA/admin
credentials; all addresses are SANs. On a healthy peer:
`sudo /usr/local/bin/k3s kubectl --server=https://<peer-IP>:6443 get nodes`.
No insecure TLS switch. Bootstrap joins use .33; replacement joins through a
survivor are separately reviewed lifecycle work, not automatic config changes.

## Approval and exact installation interface

Only after approving release, CIDRs, API/SANs, scoped firewall/controller source,
components and private lab-token generation/delivery:

```sh
export K3S_PRIVATE_DIR="$HOME/.local/share/homelab-k3s/stage-a"
make k3s-token-init K3S_TOKEN_APPROVED=yes
make k3s-install K3S_INSTALL_APPROVED=yes
# After inspecting first-run health, repeat for idempotence:
make k3s-install K3S_INSTALL_APPROVED=yes
```

Private directory: operator-owned0700 outside checkout; token0600. Exclusive
generation refuses existing files; never rerun to rotate credentials. No values
in arguments, Git, Terraform, logs or CI; no production Infisical identity.
Initial short random token travels over strict SSH. Joins use the first server's
CA-bearing secure token fetched over strict SSH, verifying its matching password
and K3s CA hash. See [token semantics](https://docs.k3s.io/cli/token).
Secret tasks use no_log; secret writes disable diff. Do not dump variables with
verbosity, custom callbacks or debug tasks.

All guests checked before mutation: identity/OS/no swap, pinned binary and state
presence. Sorted serial execution waits for local API/datastore readiness and
Node Ready before the next member. Final check requires exactly three Ready
control-plane/etcd nodes. No blanket restart handler. Identical convergence leaves
healthy services running. Binary/config drift, unmanaged state or lost existing
membership fails closed. Inspect partial failures; never wipe directories or
recreate VMs to retry. Bootstrap is not a general upgrade/recovery tool.
After its first successful service startup, an initialized marker also prevents
systemd from silently reinitializing a member whose etcd directory disappeared.

Live acceptance also needs actual etcd membership/health, CNI/DNS, TLS/network
denials, versions and second convergence. The temporary two-server phase requires
both for quorum. Stop on failures. CI cannot prove these live properties.

## Snapshot and matching token interface

After separate approval of snapshot creation/private export on a healthy cluster:

```sh
export K3S_PRIVATE_DIR="$HOME/.local/share/homelab-k3s/stage-a"
make k3s-snapshot K3S_SNAPSHOT_APPROVED=yes
```

Captures from server-1 into a unique0700 generation under the private directory:
snapshot, matching secure server-token and metadata.json. No values logged or
prior generation selected by timestamp: a unique name must match exactly one
snapshot; metadata includes snapshot/token SHA256 and pinned binary checksum. No
prior generations overwritten. Never rotate tokens during capture. Local copies
alone are not recovery from host loss; creation is not verified restoration.
On-demand snapshots are not covered by scheduled-snapshot retention; review disk
use and approve targeted pruning separately, never delete recovery data blindly.
Future Recovery Kit requires snapshot+matching token, version/checksum, shared
config/topology, Stage A state/inputs, SSH/trust prerequisites and restore
procedure. No kit implementation or iCloud/encryption redesign in this task.

## Controlled lifecycle and separately approved drills

Follow [manual upgrades](https://docs.k3s.io/upgrades/manual),
[embedded-etcd rules](https://docs.k3s.io/datastore/ha-embedded) and
[snapshot restore](https://docs.k3s.io/cli/etcd-snapshot). No automatic reset,
member-deletion or upgrade target. Never clone member disks.

| Operation | Required approved sequence and pass condition |
| --- | --- |
| One-member interruption | Approve named service only. All three healthy and snapshot/token preserved first. Stop one K3s service, not pve-lab; verify surviving API via fallback, quorum and synthetic writes. Restart same member without deleting state; require three healthy Ready members before further work |
| Lost member/replacement | Fence old identity; preserve recovery data. Review exact-version node/etcd removal and node-password cleanup. Remove only approved failed identity; join one clean replacement via survivor/secure token. Require quorum and three distinct members. Not an automatic bootstrap retry or Terraform placement change |
| Controlled upgrade | Review release/skew notes and checksum; dedicated task updates pin and upgrade implementation. Snapshot/token first, rehearse disposable upgrade. Cordon/drain one server with PDB/eviction review, no forced data loss; replace verified binary, restart that server only, wait API/etcd/Ready, uncordon. Repeat only after health returns. Servers before agents, no minor skips or unattended updater. Current bootstrap deliberately rejects a different installed binary/config |
| Failed upgrade | Stop serial progression, preserve quorum. No blind downgrade across etcd/storage formats; separately reviewed remediation or isolated restore |
| Isolated restore | Approve separate allocation and fence production/old peers. Exact recorded K3s and matching token; restore on one isolated initial server using upstream reset/restore procedure, then start normally without reset flags. Clean peers join restored server; no old member DB reuse. Compare synthetic objects, three Ready nodes, actual membership/health and fresh snapshot. Record cleanup approval |
| Two-member loss | Expected unavailable quorum, not HA success. No forced reset on original cluster; preserve evidence and use reviewed recovery |

Review hashes, version/token pairing, isolated addresses, exact restore arguments
and fencing before a drill. Reset is intentionally not a one-shot Make command.
Offline tests exercise config consistency, single init/serial order, missing or
unsafe identities/tokens, secret-safe rendering and separate action gates.
Interruption/rejoin/restore/upgrade behavior remains UNVERIFIED until live drills.

## Umask incident: proposed maintenance, not executed

2026-09-27: CoreDNS fails before exec (`stat /coredns: permission denied`,
StartError128); metrics-server exits2 (`mkdir /tmp: permission denied`). Both
are on server-1. K3s/containerd inherit the unit's UMask0077; observed snapshot
`fs` directories are root:root0700, incompatible with non-root container UIDs.
The corrected template uses0022; private configuration remains0700 and
token/config/kubeconfig remain0600. No live unit/storage changes made.

Read-only etcd preflight on all three guests: local2381 `/health` returns true;
TLS-authenticated local2382 gateway member/list, maintenance/status and alarm
queries agree on cluster12225990524396353239, three voting members, no alarms,
version3.6.14 and term2. Server-1 is leader15134591990667406597; server-2 is
17630049899303105509; server-3 is16490165289751035306. Each endpoint's applied
index equaled its Raft index (175749/175753/175757 respectively; sequential
observations, not simultaneous equality). This is actual datastore evidence,
not an inference from Node Ready. It is time-limited, not recovery proof.

### Mandatory gate before each server

Re-run these read-only checks on **all three**, locally over strict SSH:

```sh
curl -fsS --max-time 10 http://127.0.0.1:2381/health
for api in cluster/member/list maintenance/status maintenance/alarm; do
  sudo -n curl -fsS --max-time 10 \
    --cacert /var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
    --cert /var/lib/rancher/k3s/server/tls/etcd/client.crt \
    --key /var/lib/rancher/k3s/server/tls/etcd/client.key \
    -H 'Content-Type: application/json' -d '{}' \
    "https://127.0.0.1:2382/v3/$api"
done
```

Require HTTP success AND health=true, identical three voting member identities,
one agreed nonzero leader, no alarms/errors and no persistent applied-index lag.
`{}` in the alarm request means GET (no activation/deactivation). Never query
keys or export credentials. Any degraded/unreachable member, unexpected identity,
loss of quorum or sustained lag stops maintenance before another restart.
Snapshot/restore has not been qualified: obtain explicit acceptance of this
disposable-lab recovery risk, or separately authorize snapshot/token recovery
preparation first. This procedure does not create/export snapshots.

### Narrow unit-only maintenance path

Normal `k3s-install` intentionally rejects this unit drift. Keep that guard and
do not bypass it with tags, skipped assertions or a global force flag. The
smallest exception is the following reviewed unit-only operation, after explicit
live approval. It refuses any unit difference other than the approved umask.
No normal installation/convergence is run.

Use order **server-2 (.34), server-3 (.35), server-1 (.33)**, one separate
invocation at a time, never a loop. Re-evaluate leader/health before each step.
From the repository root, set `host` to the single approved guest. The template
currently contains no Jinja substitutions. These commands are NOT yet approved:

```sh
host=192.168.0.34
candidate=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes debian@"$host" 'mktemp /tmp/k3s-unit.XXXXXXXX')
scp -o BatchMode=yes -o StrictHostKeyChecking=yes \
  ansible/roles/k3s_server/templates/k3s.service.j2 "debian@$host:$candidate"
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "debian@$host" "sudo -n bash -s -- '$candidate'" <<'SH'
set -euo pipefail
candidate=$1
trap 'rm -f -- "$candidate"' EXIT
test "$(grep -c '^UMask=0077$' /etc/systemd/system/k3s.service)" = 1
cmp <(sed 's/^UMask=0077$/UMask=0022/' /etc/systemd/system/k3s.service) "$candidate"
install -o root -g root -m 0644 "$candidate" /etc/systemd/system/k3s.service
systemctl daemon-reload
systemctl restart k3s
systemctl is-active --quiet k3s
systemctl show k3s -p UMask
SH
```

Stop on any command failure; do not continue to the next host. A failed transfer
may leave only the non-secret candidate file; remove that exact file after review.
Before progressing, repeat the all-member etcd gate, require the changed node
Ready and local `/readyz` success, inspect both actual K3s and containerd process
umasks in `/proc/<PID>/status` (must be0022), and check targeted runtime errors.
With KillMode=process, do not assume a daemon-reload or unit property proves that
every surviving child inherited the new mask. If containerd retains0077, STOP
for a separately reviewed process-lifecycle action; never kill all shims.

Before server-1 maintenance verify the fallback from server-2:

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes debian@192.168.0.34 \
  'sudo -n /usr/local/bin/k3s kubectl --server=https://192.168.0.34:6443 get --raw=/readyz'
```

Use this endpoint during server-1's interruption; .33 may be unavailable and a
leader election is expected. Do not alter join addresses, SANs or kubeconfigs.
Verify three healthy members again before any further action. Existing pod
failures may persist until server-1 is repaired; any new failure stops progression.

### Existing snapshot directories

Changing umask affects future creation only, not existing0700 directories.
New writable layers may recover with0022, but cached layers/mountpoints might
still preserve restrictive modes. Do not promise restart alone will fix this.
Let normal kubelet retries run first; inspect fresh snapshot/rootfs modes and
both pod statuses/logs without deleting pods. If still blocked, map each failed
container to its exact active snapshot, merged root and relevant path modes.
Only then propose a separately approved non-recursive correction to demonstrated
incorrect root-directory metadata, with original mode/ownership recorded and
runtime coordination reviewed. No recursive chmod, image/snapshot pruning,
containerd wipe, etcd manipulation, root UID workaround or cluster recreation.
Do not relax token/config permissions. Full DNS/network qualification resumes
only after both system pods are Ready; no automatic failure drills or Flux.
