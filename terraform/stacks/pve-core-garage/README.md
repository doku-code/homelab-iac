# Garage bootstrap infrastructure

This isolated root owns only CT 209 on pve-core. Its authoritative state stays
local. Garage is rejected as the authoritative Terraform backend. Do not
migrate this root or any existing stack into Garage.

The operator allocated `192.168.0.29/24`, desired hostname `garage`, gateway
`192.168.0.1`, and DNS `192.168.0.20`. The CT uses one CPU, 1024 MiB RAM,
512 MiB swap, and a 16 GiB local-lvm root disk. It is unprivileged without
nesting. The Debian 13 template was verified on pve-core during discovery.

Run `make garage-plan` with the existing Infisical Universal Auth credentials
in the runtime environment. The target reads only the controller public SSH
key and uses the shared Infisical wrapper for Proxmox API authentication.
The CT already exists. The guest reports `garage`, but Proxmox still stores
`garage.home.arpa`. Runtime API credentials were unavailable during close-out.
Generate a NEW plan for the hostname correction: it must be an in-place update
with no replacement, destroy, network or storage changes. Stop otherwise.
Do not reuse the old creation plan. SSH access alone does not authenticate
the Terraform API provider.

After explicit approval of the saved plan, run `make garage-apply` from the
authenticated operator shell. This applies exactly `garage.tfplan` in this
root, without creating a new plan or passing replacement variable values.
Applying a saved plan does not prompt for confirmation. The target fails if
the plan is missing and uses the same Universal Auth wrapper as planning.

## Deployment gates

Garage was deployed on CT209, but FAILED the native Terraform concurrency
gate. It is unsuitable for this repository's Terraform backend requirement.
Do not migrate a canary or production state. See
[the evaluation report](../../../docs/garage-evaluation.md) for measured results.

The original deployment gates were:

- Converge Garage through Ansible only on the new CT.
- Add only VMID 209 to the existing PBS include list, preserving all existing
  entries, schedule, storage, and retention. VMID205 was already absent when
  inclusion was performed; this task did not change that entry.
- Test disposable Terraform S3 state with native `use_lockfile = true`,
  including conflicting clients, normal unlock, and stale-lock recovery.
- Revoke the disposable bucket-scoped test credential after testing.
- Stop if native locking is unreliable; do not implement custom locking.

Garage remains deployed for future general-purpose internal S3 use. The
intended service endpoint is `https://s3.doku-lab.net`, internally resolving
to Caddy at `192.168.0.24`, proxying to `192.168.0.29:3900`. This endpoint is
not yet configured. `home.arpa` remains the LAN search domain, not the primary
service URL namespace. AdGuard and Caddy are outside the repository's managed
configuration flow; see the evaluation report for narrow operator changes.

Garage has no S3 bucket versioning. Single-node recovery requires PBS coverage,
documented metadata/object paths, and a verified restore procedure. Do not
configure production Terraform backend credentials or migrate existing state.
