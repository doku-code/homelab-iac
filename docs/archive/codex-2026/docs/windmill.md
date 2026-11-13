# Windmill CE: dedicated service CT

**Status: repository implementation, not live.** CTID 210 selected, DHCP;
no live plan,
database, password, public endpoint or successful worker run is claimed.
VM208 continues to host only its monitoring Compose project. No Windmill image,
volume, network or proxy entry was created there. The temporary controller SSH
public-key copy used for inspection was removed. Pending runner edits are
unrelated; do not register a runner for this deployment.

## Placement and prerequisites

New local-state root `terraform/stacks/pve-core-windmill`, one **unprivileged**
Debian 13 CT named `windmill` on pve-core, 2 vCPU, 4 GiB RAM, 512 MiB swap,
32 GiB local-lvm. No shared monitoring, runner, NAS or hypervisor Docker daemon.
The Debian 13.6-1 library template, vmbr0, gateway .1 and AdGuard resolver .20
follow existing dedicated CTs. Only nesting and keyctl are enabled for Docker;
no devices, FUSE, mknod, privileged CT, AppArmor override or host bind mounts.
If Docker fails inside the CT, stop and diagnose; never relax isolation blindly.

1. On 2026-11-07 pve-core's cluster nextid check accepted 210, the PBS listing
   for VMID210 was empty, no explicit backup include for it was found, and
   the inventory contained no existing guest named windmill. This is an
   observation, not a permanent reservation: plan/apply check again.
2. Private ignored `terraform/stacks/pve-core-windmill/terraform.tfvars.json`
   contains only `{"ctid": 210}`. Use DHCP on vmbr0, not a guessed static
   address. The configuration target reports the single LAN address read from
   eth0 via pve-core after provisioning. Record that address after creation;
   consider reserving the lease later.
3. Use the authenticated operator shell and repo-local controller. Project ID
   comes from `.infisical.json`, environment `dev`. Universal Auth must read
   existing `/proxmox/PROXMOX_ROOT_PASSWORD`: installed Proxmox requires
   password-authenticated root@pam to set keyctl. No password in HCL/tfvars or
   CLI arguments. This permission is for the one Windmill root, not jobs.
4. Before convergence, provision service-specific secrets in `/windmill`:
   `WINDMILL_DB_PASSWORD` (random URL-safe ASCII, >=32 characters) and a distinct
   `WINDMILL_ADMIN_PASSWORD` (random, >=24 characters). Never put them in Git
   or chat. The play reads both with Universal Auth and no_log. The database
   credential is rendered only into root-only runtime configuration inside
   the CT; the admin password is passed on stdin, not stored in that file.

```sh
make windmill-plan
# Review the complete plan: exactly windmill, 1 add / 0 change / 0 destroy.
make windmill-apply WINDMILL_APPLY_APPROVED=yes
# First installation only; never use init approval to recover a missing volume.
WINDMILL_INIT_APPROVED=yes make windmill-configure WINDMILL_CONFIGURE_APPROVED=yes
```

Plan/apply recheck cluster identity and the reviewed private allocation. Apply
consumes only the saved local plan. No state migration/import or shared-host
fallback. Configure reads the CTID from this root and the DHCP address from
the guest through the hypervisor. It verifies the guest
public key over strict SSH to pve-core and pins it temporarily for Ansible.
The play refuses hosts other than a Debian 13 LXC named windmill at that IP.

## Application and access

The [official Compose at v1.864.1](https://github.com/windmill-labs/windmill/blob/v1.864.1/docker-compose.yml)
is the basis: CE server, one standard default worker and dedicated PostgreSQL18.
Images are pinned by manifest digest. No EE, custom workers, Docker socket,
privileged worker, LSP, production credentials or port published for PostgreSQL.
Use only trusted operator scripts; this minimal worker configuration is **not
a sandbox for untrusted code**. The database holds jobs, account identities and
scripts. Its explicitly owned external volume `windmill_postgres` mounts at
`/var/lib/postgresql` (PostgreSQL18 layout), not the pre-18 data path.

First access is deliberately loopback-only. After deployment, from the operator
shell, use the verified-key forward through trusted pve-core:

```sh
make windmill-address
make windmill-access
```

Open `http://127.0.0.1:18000`, login as `admin@windmill.dev` using the private
Infisical password. Fresh bootstrap changes the upstream factory password, tests
it no longer works, and refuses an unknown existing identity instead of resetting it.
The verification script checks the UI HTML and pinned API version, enqueues a
small Bash preview in the admins workspace, verifies completion, exact output
and attribution to the default worker. Ansible also performs a SQL read.

**DNS/proxy boundary:** CT200 is the existing LAN resolver and CT204 runs both
Caddy and cloudflared. No shared proxy reload, public DNS, tunnel change or DNS
rewrite is part of initial bootstrap. An internal hostname is not itself access
control. Before adding a LAN-only Caddy route, review tunnel ingress, explicitly
restrict the CT listener to the proxy and prove it unreachable from WAN/tunnel.
Until that is verified, keep the SSH forward; there is deliberately no working
Caddy FQDN claimed here.

## Maintenance and recovery

Run `make windmill-configure WINDMILL_CONFIGURE_APPROVED=yes` for convergence
and the one smoke job. On the CT use `cd /opt/windmill && docker compose ps`.
Never publish full Compose interpolation or container environments. Do not use
`down -v`, prune, or reinitialize a missing database. Back up the dedicated CT
and a restricted **whole PostgreSQL cluster** logical dump (includes roles),
confirm PBS coverage for its allocated identity and qualify an isolated restore
before relying on it. No backup coverage or restore is asserted. Update pins
only after backup and migration review; never change database major casually.

## Automation inventory

- Safe candidates: repository format checks; static Compose validation; read-only
  job/health queries. The initial smoke has no access to other infrastructure.
- `scripts/check-quality.py` and the repository's mock Terraform tests run in a
  checkout with the existing CI toolchain; they need no production credentials.
- `scripts/verify-recovery-kit.py`, `scripts/qualify-pg-backend.py`, K3s helpers
  and the saved-plan Make targets have different data/privilege boundaries:
  inventory them, do not blindly schedule them as Windmill jobs.
- Later a reviewed flow can dispatch an existing trusted controller for an
  OpenTofu/Terraform plan, record the exact SHA/plan, wait for operator approval,
  apply only that artifact, then invoke the existing bounded Ansible playbook.
  The repo currently uses Terraform; OpenTofu compatibility is not verified.
  Do not export Proxmox root, SSH keys or an all-purpose Infisical identity into
  the default worker. No management VM, runner deployment or Git sync here.
