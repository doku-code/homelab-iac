# Redundant Tailscale subnet routers

Task [150-F](../tasks/150-f-tailscale-routers.md) records current live evidence.
The operator created CT306/307; verified SSH enrollment is complete. Guest
convergence currently stops at missing controller Universal Auth credentials
on the first router. Tailnet registration, route approval and failover remain
unverified. Do not repeat Terraform apply to resolve this authentication gate.
The operator supplied the existing pve-infra preferences: route 192.168.0.0/24,
SNAT enabled, Tailscale SSH disabled. The dated [inventory](pve-infra-evacuation.md)
remains historical evidence, not an allocation registry.

## Ownership and prerequisites

- Terraform root `terraform/stacks/pve-tailscale-routers`, independent LOCAL state:
  exactly two new CTs, no imports or changes to any existing root. There is no
  generic LXC module in this repository; this follows the small service CT roots.
- `ts-router-01` on pve-k8s-01/.16; `ts-router-02` on pve-k8s-02/.17.
  Each: Debian 13 amd64, unprivileged, 1 vCPU, 512 MiB RAM, 256 MiB swap, 8 GiB rootfs,
  started/onboot, one existing bridge/NIC, no nesting. Provider 0.112.0 uses
  `device_passthrough` for `/dev/net/tun` (0666); no host edits or privileged CT.
- Ansible role `tailscale_subnet_router` owns guest packages, forwarding, daemon
  and preferences. Native Tailscale redundant subnet routing, NOT physical
  Kubernetes HA, VRRP, a VIP or a second tailnet.
- **Operator allocation now recorded:** see [150-F evidence](../tasks/150-f-tailscale-routers.md#approved-allocation-and-plan-attempt---2026-09-29).
  The ignored operator profile is populated; local-lvm follows CT201/CT200 on
  the respective nodes. Cluster VMID absence and template availability were
  checked read-only before creation. No IP scan was run. The operator subsequently
  reported successful apply: 2 added, 0 changed, 0 destroyed.
- Confirm each node's capacity, local rootfs storage, existing bridge (`vmbr0`
  default), Debian 13 template volume ID and provenance. The example 13.6-1 filename
  follows existing CTs but is NOT evidence that this image exists on these nodes.
  No image is downloaded/imported by this root.
- Proxmox must support the `devN` device API, and the existing provider identity
  must be authorized to create these CTs with TUN. Do not bypass a permission
  failure by making CTs privileged, enabling nesting or editing host config.
- Existing gateway 192.168.0.1 / DNS 192.168.0.20, outbound Debian/Tailscale HTTPS,
  Tailscale control/DERP and peer connectivity, and guest SSH must be permitted
  by the existing firewall. No cluster/host firewall policy is changed here.
  Retain an independent management path during cutover.

## Private inputs and commands

Run from the repository root, using the existing controller environment.
Copy `terraform/stacks/pve-tailscale-routers/terraform.tfvars.example` to the
ignored `terraform.tfvars` in that directory; replace all TODOs, including the
two invalid zero VMIDs. No allocation is silently selected. The tracked public
administration key is the default; `management_ssh_public_key` accepts a different
public key. Never supply a private key or Tailscale credential to Terraform.

Use existing Universal Auth runtime variables `INFISICAL_CLIENT_ID` and
`INFISICAL_CLIENT_SECRET`. Tailscale plan/apply alone use the scoped
`scripts/tailscale-proxmox.py` adapter: the same pinned SDK/Universal Auth and
`infisical run` pattern as Stage A, project from `.infisical.json`, environment
`dev`, path `/proxmox/`. It requires the injected `PROXMOX_ROOT_PASSWORD`.
There is no ambient-password fallback, manual password export or token fallback.
Infisical shell-parameter expansion and imported secrets are disabled so a literal
password (including dollar signs) comes from the selected folder without rewriting.
The shared `INFISICAL_RUN` wrapper and every other stack remain unchanged.
Review API certificate trust: verification defaults ON; `proxmox_insecure` is
the existing explicit opt-in, not a fallback. Do not disable TLS to fix auth.

### Root-only device passthrough

The operator's first apply was rejected: device passthrough requires password
authentication as `root@pam`, not an Administrator API token. Do not infer guest
existence or absence from that failure. The operator must check live VMIDs306/307
and local state before another apply; never auto-import, reset state or adopt
an unexpected guest. TUN, unprivileged mode and all allocations remain unchanged.

Only `proxmox_virtual_environment_container.router` (the two instances) uses
`proxmox.root`. This alias sets `username="root@pam"`, clears `api_token`, and
inherits the existing endpoint/TLS variables. The runtime adapter maps the
Infisical-injected `PROXMOX_ROOT_PASSWORD` to BPG's `PROXMOX_VE_PASSWORD` solely
in the Terraform subprocess; it removes token/ticket/legacy authentication,
Infisical credentials and TF_VAR inputs from that subprocess environment.
Use the private native tfvars for non-secret configuration. This root must not
be expanded to unrelated resources under this privileged runtime.

No password Terraform variable, output or resource argument exists. The runtime
password is not serialized into saved plans/state by this configuration; those
files still contain private infrastructure metadata and must remain protected.
Provider debugging/TF_LOG and TF_CLI_ARGS overrides are rejected. No shell
expansion or command argument carries the password. Privileged local processes
can inspect process memory/environment: run only on the trusted controller.
The adapter uses Infisical session-token environment injection, not CLI credential
arguments. Do not enable external tracing or environment dumps.

Generate and review a NEW plan after this provider change. The Make plan target
invalidates the old saved plan; apply rejects a saved plan using the old provider.
No live apply is authorized by this correction. See the pinned
[BPG authentication implementation](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/provider/provider.go).

```bash
make tailscale-check
make tailscale-plan
terraform -chdir=terraform/stacks/pve-tailscale-routers show tailscale.tfplan
# Only after reviewing exactly 2 additions, 0 changes, 0 destroys:
make tailscale-apply TAILSCALE_APPLY_APPROVED=yes
# Verify and pin guest SSH keys using the procedure below.
# Then, explicitly approve guest convergence:
make tailscale-configure TAILSCALE_CONFIGURE_APPROVED=yes
```

Apply uses ONLY the saved plan, with Terraform's stale-state checks. Never
reinitialize a missing authoritative state to adopt existing CTs. Plan deletes
its previous saved plan before attempting another. Do not change private inputs
between plan review and apply. Capture this root's state for recovery after
deployment using the existing recovery contract, not Git or a second live state.

### Verify guest SSH trust before first convergence

Never treat `ssh-keyscan` as authentication. Using an already trusted SSH
connection to the owning Proxmox node, read ONLY the guest public host key:

```bash
# On pve-k8s-01 for CT306; use CT307 on pve-k8s-02:
pct exec 306 -- cat /etc/ssh/ssh_host_ed25519_key.pub
pct exec 306 -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
# On the controller, collect the candidate, NOT yet trusted:
ssh-keyscan -T 8 -t ed25519 192.168.0.36
ssh-keygen -F 192.168.0.36 -f ~/.ssh/known_hosts
```

Repeat for `.37`. Compare the complete ED25519 key type/base64 and SHA256
fingerprint against the authoritative public key read inside that specific CT.
Stop on any mismatch or conflicting existing trust record; do not remove or
replace existing entries automatically. Only after both comparisons succeed,
append each verified `IP ssh-ed25519 BASE64_PUBLIC_KEY` line to the operator's
normal `~/.ssh/known_hosts`, preserving other entries. Never copy a private key.
Confirm each hostname with `ssh -o BatchMode=yes -o StrictHostKeyChecking=yes
root@IP hostname` before convergence. Do not disable checking or use blind TOFU.

For this deployment, the trusted controller connection to pve-core/.11 reached
each owner using the existing cluster-managed public trust file
`/etc/pve/nodes/NODE/ssh_known_hosts`, `HostKeyAlias=NODE`, and
`StrictHostKeyChecking=yes`. This is an alternative trusted path, not permission
to enroll an unknown Proxmox key blindly. Fingerprints and results are recorded
in [Task 150-F](../tasks/150-f-tailscale-routers.md#ssh-enrollment-and-partial-convergence---2026-09-30).

If first registration stops because Universal Auth is absent, rerun the same
`make tailscale-configure TAILSCALE_CONFIGURE_APPROVED=yes` from the authenticated
operator shell. Do not export the Tailscale key manually or bypass the guard.

Convergence derives a temporary private inventory from this root's outputs,
uses strict OpenSSH host-key checking and runs serially. Only root SSH into the
two new guests is used, not a connection to pve-infra or Proxmox hosts.
The collection-based Universal Auth/read equivalent of `infisical run` executes
on the controller ONLY when a guest reports `NeedsLogin`. It requests:

`Homelab-IaC / dev / /tailscale/TS_AUTH_KEY_SUBNET_ROUTER`

This is the only new workload secret. Its Machine Identity must be allowed to
read that path. The operator supplied that it is reusable/non-ephemeral and
belongs to the EXISTING tailnet; these properties require operator confirmation,
not inference from an opaque key. No secret is created, rotated or copied here.

The key reaches `tailscale up --auth-key=file:/dev/stdin` through command stdin,
with SSH pipelining enabled and retained remote module files forbidden. Secret
tasks use `no_log: true`; Infisical calls are delegated locally. Do not enable
debugging, alternate logging/callbacks, fact caching or remote module retention
for this operation. `/dev/stdin` is a pipe, not a stored key file. No async task,
shell interpolation or secret command-line argument is used for registration.
Subsequent `Running` guests skip ALL Infisical reads and use only `tailscale set`
on owned preference drift; they need no bootstrap key. A stopped daemon state,
pending machine approval or unexpected state fails closed for operator review.
An expired node may need reauthentication (`NeedsLogin`); its local identity
is never deleted or force-reset. Do not run bootstrap with `--check --diff`;
use the offline syntax/tests and review before approved convergence.

## Guest configuration

Tailscale 1.102.4 is pinned from the official signed Debian trixie stable APT
repository. The signing key is SHA256-pinned. No curl-to-shell installer. Update
the pin deliberately, rerun checks and converge one new router at a time in an
approved window; no package downgrade is allowed automatically.

Persist IPv4 AND IPv6 forwarding per Tailscale's standard Linux router guidance.
IPv6 forwarding does NOT advertise an IPv6 prefix or an exit route; the sole
advertisement remains 192.168.0.0/24. No SLAAC/IPv6 gateway is configured by this
profile. Keep `accept-routes=false`, `ssh=false`, `advertise-exit-node=false`,
no selected exit node, SNAT enabled and netfilter mode on. `accept-dns=false`
keeps the existing Proxmox-provided LAN resolver rather than letting tailnet DNS
rewrite it. Hostname comes from the same Terraform identity as inventory.

## Operator live verification and cutover (not executed)

1. Confirm both CTs boot/onboot, remain unprivileged and expose TUN. Verify
   hostname/IP/gateway/DNS, SSH, service and forwarding inside EACH new guest:
   `systemctl is-enabled tailscaled`, `systemctl is-active tailscaled`,
   `sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding`,
   `test -c /dev/net/tun`, `tailscale ip -4`.
2. Inspect `tailscale status` privately. For JSON, filter ONLY public fields:
   `tailscale status --json | jq '{BackendState, Self: {ID: .Self.ID, TailscaleIPs: .Self.TailscaleIPs}}'`.
   Require different Self IDs and Tailscale IPs on01/02, matching machines in
   the EXISTING tailnet, non-ephemeral registrations and expected key-expiry
   policy. Do not publish peer lists, raw preferences or private state.
3. Filter `tailscale debug prefs` with
   `jq '{AdvertiseRoutes, RouteAll, NoSNAT, RunSSH, ExitNodeID, CorpDNS, Hostname}'`.
   Require exact route `["192.168.0.0/24"]`, RouteAll/NoSNAT/RunSSH/CorpDNS false,
   empty ExitNodeID. Advertising does not prove route approval or reachability.
4. In the existing Tailscale admin console, approve the new devices if required
   and approve ONLY 192.168.0.0/24 on BOTH. Check existing ACL/grant access and
   tailnet-lock requirements; do not broaden policy or approve exit routes.
   If device approval paused bootstrap, approve it and rerun convergence.
5. From a tailnet client OUTSIDE the LAN, verify an authorized LAN service and
   route acceptance (Linux clients require accept-routes). Record the path in
   use and expected access restrictions, not just a successful Tailscale ping.
6. With independent local management available, stop `tailscaled` on ONE NEW
   router only (`systemctl stop tailscaled`). Verify the same LAN service
   continues via the OTHER NEW router; allow documented failover delay. Restore
   with `systemctl start tailscaled`, confirm health, then test the reverse.
   While pve-infra still advertises, success alone is NOT proof of new-pair
   failover: confirm the selected route/traffic on the surviving new router.
   Record ambiguous path evidence as unverified, not PASS.
7. Only after reviewed new-route evidence, in an approved cutover window,
   disable the OLD host's service: `systemctl disable --now tailscaled` on
   pve-infra ONLY. Preserve its state/device and independent management for
   rollback. Verify remote LAN access, then repeat the new-router one-at-a-time
   failover tests with the old service stopped to eliminate a hidden fallback.
   Restore each new service immediately after its test. Stop if remote access
   fails; restore the old service (`systemctl enable --now tailscaled`) and
   investigate rather than deleting identities or changing routes blindly.
8. Only after final remote access/failover acceptance, remove the obsolete
   pve-infra DEVICE in the Tailscale admin console. Do not copy its state.
   Removing pve-infra from the Proxmox cluster is a SEPARATE operator action.

Do not promise zero packet loss or uninterrupted existing sessions. A failed
test blocks retirement. This task grants none of the above live permissions.

## Backup and recovery

Both CTs use normal storage-backed rootfs, no bind-mounted data. Have the
operator include the two approved VMIDs in the existing PBS job after creation;
do not change its schedule, retention or unrelated inclusions. Coverage and
restore are NOT yet verified. Each CT backup can retain its OWN persistent
`/var/lib/tailscale/tailscaled.state`; treat backups as sensitive identity data.
Never read/export this file in normal checks, clone it into the other router or
boot a restored copy alongside its original. Restore only the same machine
identity with its original offline, or separately approve a genuinely new node.

## Upstream references

- [Official Debian packages](https://pkgs.tailscale.com/stable/#debian-trixie)
- [Unprivileged LXC TUN access](https://tailscale.com/kb/1130/lxc-unprivileged)
- [Subnet-router forwarding and approval](https://tailscale.com/kb/1019/subnets)
- [Native redundant-router behavior](https://tailscale.com/kb/1115/high-availability)
- [Auth-key file input](https://tailscale.com/kb/1241/tailscale-up)
- [Pinned provider device passthrough](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_container.md)
