# Stage A headless VM profile

Task [100](../tasks/100-stage-a-headless-vms.md): live guest baseline verified on
2026-09-26, awaiting operator acceptance. Operator applied four additions and
started VMs303-305; guest qualification and two baseline runs now succeeded.
K3s belongs to Task 110; these guests do not install it automatically.

## Ownership and inputs

`terraform/stacks/pve-lab-k3s` is a separate local backend/authority. Its new
`module.servers["server-1"..."server-3"].proxmox_virtual_environment_vm.this`
addresses own only these lab VMs. `proxmox_download_file.linux` keys are
`node/image_datastore`; three VMs on one datastore/node share one checksummed
cloud image. Operator-reported apply: four additions, no changes or destroys.
No imports, moves or address changes to any existing root, including the
undeployed controller. The reusable module lives in `terraform/modules/headless-vm`.
The existing workstation Terraform, state, GPU/USB and host arbitration remain
unchanged. No workstation host role is used by this baseline.

No VMID or IP defaults exist. Do not create private inputs before allocation
review. Later, ignored `terraform.tfvars` must supply:

| Input | Required reviewed value |
| --- | --- |
| `proxmox_endpoint`, `proxmox_insecure` | Existing provider/Universal Auth convention; explicit reviewed TLS choice, no new credential mechanism |
| `image.url`, `image.sha256` | Versioned/dated Debian 13 AMD64 HTTPS cloud image and verified SHA256; no mutable latest URL |
| `servers` | Exactly `server-1`, `server-2`, `server-3` |
| Each server | Unique `vm_id`, `name`, `ipv4` CIDR; `node`, `bridge`, `gateway`, nonempty `dns_servers`, `image_datastore`, `disk_datastore`, `storage_local = true` |
| Optional sizing per server | Defaults: `cores = 2`, `memory = 4096` MiB, `disk_gb = 32` GiB; minimums match proposal |

`storage_local` is an operator declaration, not discovery: prove the actual
datastore is local SSD-backed before plan. Both system and cloud-init use it.
The fixed repository-managed public SSH key creates the Debian cloud user;
no private key, password or token enters configuration/state. Provider auth
continues through `INFISICAL_RUN`/Universal Auth at execution time.

Operator dedicates pve-lab's 32-GB physical memory and CPU to the experiment,
minus measured Proxmox overhead and safety headroom. Workstations remain off;
this task neither stops nor modifies them. Proposed VM RAM total is 12 GiB.
Confirm measured overhead, at least 2 GiB additional headroom and local capacity
before accepting allocation. Stage A is still one physical failure domain.

## Interfaces and approval gates

Safe local check: `make stage-a-check`. Mocked Terraform tests use disposable
code-only copies, synthetic documentation IPs and mocked providers, not live
state, private inputs or a provider-backed plan.

The initial apply/start/baseline approvals are completed, not standing permission
for further changes. Operational interfaces retain separate explicit gates:

1. `make stage-a-plan STAGE_A_ALLOCATION_REVIEWED=yes` after fresh allocation,
   host/storage/network/trust checks. Deletes the previous saved plan before
   initialization/authentication; removes partial output on failure. Review
   resource scope and the printed SHA256. No automatic apply.
2. `make stage-a-apply STAGE_A_APPLY_APPROVED=yes STAGE_A_PLAN_SHA256=<reviewed-hash>`
   after exact-plan approval. Applies only `stage-a.tfplan`, removes it after
   success, creates stopped VMs (`on_boot` false). Never bypass stale-state checks.
3. `make stage-a-start STAGE_A_START_APPROVED=yes` after separate start approval.
   Reads inventory from this root's applied local state, uses existing trusted
   SSH access as root to each Proxmox node, verifies VM name/ID and starts only
   those stopped VMs. Make also loads the existing homelab inventory, resolving
   the delegate pve-lab to its management IP 192.168.0.14 without relying on DNS.
   Missing delegate mappings fail closed; host-key checking remains enabled.
   No host package/configuration changes or host-wide commands.
4. `make stage-a-configure STAGE_A_CONFIGURE_APPROVED=yes` after guest SSH trust
   verification. Uses Debian user/sudo and generated inventory, serially.

Start/converge use a mode-0600 `inventory.json` in a private temporary directory
and delete both on exit. The JSON extension is required for reliable Ansible
inventory plugin selection and is tested with the actual inventory parser. No
parallel hand-maintained host list. Host key verification is never disabled.
Prefer independent node/guest identity verification. For initial enrollment of
VMs303-305 only, the operator explicitly approved `StrictHostKeyChecking=accept-new`
in normal known_hosts; this TOFU exception did not independently authenticate
first contact. Subsequent SSH and Ansible used `StrictHostKeyChecking=yes`;
conflicts must stop work, never overwrite keys. Losing local
state is a recovery incident, not permission to synthesize another inventory.

OS baseline refreshes APT metadata, installs CA/curl/Python/QEMU guest agent/time
sync prerequisites, sets the reviewed hostname and enables agent/time services.
It does not install Terraform, Ansible, K3s, Docker, GPU drivers or Flux, alter
SSH policy/network/storage, or inject Infisical credentials. Cloud-init owns
network/user/key initialization; baseline owns ordinary guest OS packages/services.

## Validation and stop conditions

Mock tests cover uniqueness, explicit allocation, 4-GiB sizing, local-storage
intent, immutable image/checksum, deduplicated image count, alternate placement,
inventory output and stopped/no-passthrough lifecycle. Existing workstation
snapshot assertions remain unchanged. Static Ansible/render and Make denial
tests do not prove guest idempotence or host capacity.

Live evidence: all three Debian13.7 guests have expected names/.33-.35 addresses,
32-GiB local disks, working debian SSH/sudo, gateway .1, resolver .20 and NTP sync.
Cloud-init completed with no errors but a deprecated string-user warning; this
does not prove compatibility with a future cloud-init release. QEMU agent is
active and answers Proxmox; time service active/enabled; no failed systemd units.
First baseline: two changes per guest (agent install/start); second: zero changes,
zero failures/unreachable. Full recaps are in Task100, not merely syntax evidence.
Workstations remain off per operator and unchanged. `prevent_destroy` stays enabled. Stop
on any existing-resource drift; do not delete guests or discard state to retry.
Changing host placement is not an etcd migration. No K3s bootstrap before Task
110 is assigned and approved. Stage A is the seventh real local state authority;
see [current recovery inventory](recovery-kit-preparation.md#stage-a-authority-update---2026-09-26).
No state export or backend change is authorized by this runbook.
