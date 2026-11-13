# Stage A headless VM profile

Task [100](../tasks/100-stage-a-headless-vms.md): live guest baseline verified on
2026-09-26 and accepted by the operator; Task100 is DONE. Operator applied four additions and
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
| `proxmox_endpoint`, `proxmox_insecure` | HTTPS API; TLS verification defaults on. Trust your CA; do not bypass TLS for portability |
| `ssh_public_key` | Optional Ed25519 public string via tfvars or TF_VAR_ssh_public_key; null/omission preserves keys/doku-lab-admin.pub |
| `image.url`, `image.sha256` | Versioned/dated Debian 13 AMD64 HTTPS cloud image and verified SHA256; no mutable latest URL |
| `servers` | Exactly `server-1`, `server-2`, `server-3` |
| Each server | Unique `vm_id`, `name`, `ipv4` CIDR; `node`, `bridge`, `gateway`, nonempty `dns_servers`, `image_datastore`, `disk_datastore`, `storage_local = true` |
| Optional sizing per server | Defaults: `cores = 2`, `memory = 4096` MiB, `disk_gb = 32` GiB; minimums match proposal |

`storage_local` is an operator declaration, not discovery: prove the actual
datastore is local SSD-backed before plan. Both system and cloud-init use it.
The selected public SSH key creates the Debian cloud user; the unchanged default
preserves current VMs. No private key, password or token enters configuration/state.
Both input sources use this same root, local state, profile and saved plan.

## Explicit sources and Starter example

Task045 implements only Stage A Terraform input delivery, tested offline.
`STAGE_A_INPUT_SOURCE` is required for plan/apply: exactly `infisical` or `private`.
There is no default or fallback. Existing operators now explicitly select
`infisical`; their credentials, project metadata and native tfvars stay unchanged.
Start/configure/check do not use provider credentials and need no selector.

Infisical uses existing `INFISICAL_CLIENT_ID`/`INFISICAL_CLIENT_SECRET`, the Make
domain/environment defaults and .infisical.json project. Universal Auth uses the
already pinned Python SDK so credentials never enter process arguments;
`infisical run` receives its short-lived token via environment, then validates
the exported provider token. Ambient Proxmox auth cannot mask a missing export.
See [CLI environment-token support](https://infisical.com/docs/cli/commands/run).
Other stacks' existing INFISICAL_RUN macro is unchanged.

Private mode uses only `PROXMOX_VE_API_TOKEN` from the runtime environment
(`user@realm!token=value`), not an Infisical identity/session/CLI. Set up the
repository .venv, Terraform and an appropriately scoped Proxmox API identity.
Native Terraform validates required profile variables with `-input=false`;
missing/invalid credentials and selectors fail before provider operations.
Conflicting username/password/OTP authentication, TF_LOG*, TF_CLI_ARGS* and
non-default TF_WORKSPACE are rejected. Do not enable shell tracing or put tokens
in Make arguments/tfvars. Valid syntax does not prove remote ACLs or reachability.

For a NEW environment in a fresh checkout with no existing state, after reviewing
allocations, storage, network and API trust:

```bash
make setup-controller
# Stop if terraform.tfvars already exists; never overwrite an existing environment.
test ! -e terraform/stacks/pve-lab-k3s/terraform.tfvars || { echo 'Existing inputs: stop'; exit 1; }
cp terraform/stacks/pve-lab-k3s/terraform.tfvars.example terraform/stacks/pve-lab-k3s/terraform.tfvars
chmod 600 terraform/stacks/pve-lab-k3s/terraform.tfvars
```

Edit that ignored file with your infrastructure profile, replacing ALL example
addresses/IDs/image placeholders. No secret goes in it. Use your own public key
either as `ssh_public_key` there or the environment below, not both (tfvars takes
precedence). Run in Bash, with shell tracing disabled, after plan authorization:

```bash
set +x
export TF_VAR_ssh_public_key="$(cat "$HOME/.ssh/id_ed25519.pub")"
test -n "$TF_VAR_ssh_public_key" || exit 1
read -r -s -p 'Proxmox API token (user@realm!token=value): ' PROXMOX_VE_API_TOKEN
printf '\n'
export PROXMOX_VE_API_TOKEN
make stage-a-plan STAGE_A_INPUT_SOURCE=private STAGE_A_ALLOCATION_REVIEWED=yes
unset PROXMOX_VE_API_TOKEN
```

The token is not a Terraform variable or CLI argument. Protect the ignored local
state and saved plan. Review every resource and the printed plan SHA before a
separately approved apply; reload credentials securely in the same manner:

```bash
make stage-a-apply STAGE_A_INPUT_SOURCE=private STAGE_A_APPLY_APPROVED=yes STAGE_A_PLAN_SHA256=<reviewed-hash>
```

Infisical-backed equivalent (existing identity already exported securely):

```bash
make stage-a-plan STAGE_A_INPUT_SOURCE=infisical STAGE_A_ALLOCATION_REVIEWED=yes
make stage-a-apply STAGE_A_INPUT_SOURCE=infisical STAGE_A_APPLY_APPROVED=yes STAGE_A_PLAN_SHA256=<reviewed-hash>
```

Apply consumes ONLY the hash-reviewed saved plan, not updated tfvars; Terraform's
stale-state check remains enabled. Failed plan/auth removes partial saved plans;
failed apply preserves the plan for investigation. Source selection never chooses
a new state or recovers a missing state: losing existing state remains an incident.
This Starter example is not a Recovery Kit generator, restore command or generic
multi-environment manager. External Proxmox SSH delegate mappings are still needed
before start, and guest SSH trust before configure; no Ansible interface changed.

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

1. `make stage-a-plan STAGE_A_INPUT_SOURCE=infisical STAGE_A_ALLOCATION_REVIEWED=yes` (or private) after fresh allocation,
   host/storage/network/trust checks. Deletes the previous saved plan before
   initialization/authentication; removes partial output on failure. Review
   resource scope and the printed SHA256. No automatic apply.
2. `make stage-a-apply STAGE_A_INPUT_SOURCE=infisical STAGE_A_APPLY_APPROVED=yes STAGE_A_PLAN_SHA256=<reviewed-hash>` (or private)
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
