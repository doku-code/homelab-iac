# Deployment inputs, Starter Kit and Recovery Kit

Metadata inventory, 2026-09-27. No private tfvars, states, tokens or credential
values were inspected. [Architecture](architecture.md) owns decisions; this
document describes code interfaces, not a working universal deployment command.
R = required; O = optional/defaulted; S = sensitive; N = non-secret metadata.
Do not put secret values in CLI arguments, Git, example files or logs.

## Starting point and workflow safety

Current supported infrastructure provider is Proxmox; no other hypervisor is
implemented. Supply reachable API/SSH, verified trust, authorized identity,
allocated IDs/IPs, bridge/gateway/DNS, suitable datastores/templates and measured
capacity. OS roles need compatible guests and sudo; downloads need internet or
a separately qualified artifact cache. Stateful apps additionally need suitable
persistent storage and an explicit fresh/restore decision. GitHub/public source
is not a copy of private inputs or application data.

`setup-controller`, syntax checks and CI are not deployment. `plan` reads live
infrastructure and may write a sensitive local plan. `apply`, `configure`,
`bootstrap`, `start` and snapshots can mutate live systems; runbook approvals
apply. `workstations-check` contacts live hosts in check mode, not offline.
`runner-live-check` authenticates/reads secrets despite its check-mode flag.
Historical `runner-import`/`runner-live-plan` target retired ownership and must
not be used for PostgreSQL CT300. Select only the intended stack and state.

## Controller and credential delivery

| Actual input | Purpose / consumer | Requirement, format, sensitivity | Current source / alternative today |
| --- | --- | --- | --- |
| `CONTROLLER_PYTHON` | Make recreates .venv | O, executable path, N; Python compatible with pinned requirements | Shell/Make, default python3; explicit standalone Python in CI |
| `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET` | Universal Auth in Make and runner playbook | R for these workflows; identity string + secret string, protect both | Operator runtime; no non-Infisical Make selector implemented |
| `INFISICAL_DOMAIN`, `INFISICAL_ENV`, `INFISICAL_PROJECT_ID` | Make Infisical wrapper | O defaults; HTTPS URL, slug, project ID, N | Make overrides; project derives from tracked .infisical.json workspaceId |
| `PROXMOX_VE_API_TOKEN` | bpg provider environment auth | R when using API-token auth; `user@realm!token=VALUE`, S (format only) | Injected environment in normal Infisical workflow; provider accepts explicit environment independently, wrappers still force Infisical |
| `ansible_host`, `ansible_user`, `ansible_ssh_private_key_file`, SSH agent/known_hosts | Ansible SSH connection | Host/user R; key path optional to SSH defaults, N metadata; key bytes S, never copied | Static or generated inventory; standard Ansible overrides, not an alternative whole-stack adapter |
| `GUEST_SSH_PRIVATE_KEY_FILE` | Guest/runner/Garage/tfstate inventory | O, controller path, default ~/.ssh/id_ed25519; key S | Runtime env; no Infisical call in these inventory lookups |
| `PROXMOX_URL`, `PROXMOX_USER`, `PROXMOX_TOKEN_ID`, `PROXMOX_TOKEN_SECRET` | Dynamic guests.proxmox inventory | R; HTTPS URL / user@realm / token name N, token secret S | Runtime env directly; not bpg's combined-token name |
| `GUEST_LINUX_USER`, `GUEST_WINDOWS_USER`, `LIMIT` | Dynamic guest group vars / guests-apply | Users R for corresponding OS; LIMIT R for apply, N, e.g. `dev` | Runtime env / Make; existing authenticated guest SSH and Windows prerequisites required |

TLS varies today: monitoring/workstations/example hardcode insecure provider
settings; newer roots expose a boolean. This is a portability/security gap, not
a recommended universal TLS bypass. No credentials were queried to confirm
which secret exports are present. Provider auth must be verified for each future
private-input path before it can be called supported.

## Terraform roots

All variables below are N; private tfvars as a whole remain private. These are
deployment configuration, NOT restored guest disks or application data. Native
Terraform supports reviewed tfvars / TF_VAR inputs independently of Infisical;
current plan/apply Make wrappers listed here still mandate Universal Auth.
Required object fields/types/validation remain authoritative in linked HCL.

| Root / interface | Actual variables, requirement and purpose | External constraints / present portability |
| --- | --- | --- |
| [Stage A](../terraform/stacks/pve-lab-k3s/variables.tf), stage-a-* | `proxmox_endpoint` R HTTPS URL; `proxmox_insecure` O false; `image.url`, `image.sha256` R dated Debian HTTPS/64-hex integrity; `servers` R three-key map | Same root supports node placement inputs, not safe automatic etcd migration; source wrapper Infisical. Public SSH key fixed by root to keys/doku-lab-admin.pub; not yet selectable for another user |
| [Controller](../terraform/stacks/pve-lab-controller/variables.tf), controller-* | `proxmox_endpoint` R; `proxmox_insecure` O false; `profile` R object | Undeployed optional adapter; fixed public key, private reviewed profile required; Infisical wrapper |
| [Workstations](../terraform/stacks/pve-lab-workstations/variables.tf), workstations-* | `proxmox_endpoint` R; `hardware_profiles` O {} in [hardware.tf](../terraform/stacks/pve-lab-workstations/hardware.tf): gpu bool, usb_mappings list per known workstation | Existing adopted guests and named GPU/USB mappings, not generic OS creation. Fixed topology, Infisical wrapper; apply also runs host Ansible |
| [Monitoring](../terraform/stacks/deb13-monitoring/variables.tf) | `proxmox_endpoint` R | Fixed VM208/image/network definition; no dedicated monitoring Terraform Make interface; native Terraform input possible, not fully portable |
| [Active runner CT301](../terraform/stacks/pve-compute-forgejo-runner-migration/variables.tf), runner-migration-* | `proxmox_endpoint` R; `proxmox_insecure` O true; `management_ssh_public_key` R OpenSSH Ed25519 public string; `dns_servers` O list | Fixed CT/node/network/template; existing Forgejo/registry needed for configured jobs. Private tfvars + Infisical provider wrapper |
| [Garage](../terraform/stacks/pve-core-garage/variables.tf), garage-* | `proxmox_endpoint` O operator endpoint; `proxmox_insecure` O true; `management_ssh_public_key` R public string | Fixed CT209/template/storage/network; rejected as Terraform backend. Make `GARAGE_SSH_PUBLIC_KEY_FILE` O defaults ~/.ssh/id_ed25519.pub, injects TF_VAR_management_ssh_public_key; Infisical wrapper |
| [PostgreSQL](../terraform/stacks/pve-core-tfstate/variables.tf), tfstate-* | Same three variable names/requirements as Garage | Fixed CT300/bootstrap local authority; not Infisical DB, no state migration. `TFSTATE_SSH_PUBLIC_KEY_FILE` O same public-file default; Infisical wrapper |
| [Cloud example](../terraform/examples/cloud-image-vm/variables.tf) | `proxmox_endpoint` R | Fixed example VM/image/network and repository public key; not an allocated supported generic environment |
| [Historical runner](../terraform/stacks/pve-compute-forgejo-runner/variables.tf) | See quarantined fields below | Recovery evidence only; NOT an entry point for new deployments |

Stage A `servers` keys are exactly `server-1`, `server-2`, `server-3`. Each
requires `node`, `vm_id`, `name`, `image_datastore`, `disk_datastore`,
`storage_local` (true), `bridge`, `ipv4`, `gateway`, `dns_servers`.
`cores`, `memory`, `disk_gb` are O defaults2/4096/32. Safe formats: reviewed
integer VMID, `lab-node`, `192.0.2.33/24`, gateway `192.0.2.1`, DNS list of IPs;
documentation addresses are not allocations. Controller `profile` has the same
fields except `storage_local`, adds required `image_url`/`image_sha256`, and
requires explicit sizing. Reuse [Stage A](k3s-stage-a.md) and
[controller](headless-controller.md) examples rather than a second schema.

Historical runner required fields: `proxmox_endpoint`, `vm_id`, `unprivileged`,
`rootfs_datastore_id`, `rootfs_size`, `operating_system_template_file_id`,
`network_bridge`, `network_mac_address`, `network_firewall`,
`network_ipv4_address`, `network_ipv4_gateway`, `cpu_cores`, `memory_mib`,
`features`, `tags`, `started`, `on_boot`. Optional: `proxmox_insecure=false`,
`operating_system_type=debian`, `swap_mib=0`, `management_ssh_public_key=null`.
Formats are the linked HCL types (IDs/paths/strings, booleans, GiB/MiB numbers,
CIDR, MAC, feature object/tag set); exact old values must come from reviewed
recovery evidence, not be guessed from the current CT300.

## Ansible application and cluster interfaces

| Workflow / actual names | Requirement, purpose, format and sensitivity | Current source / gap |
| --- | --- | --- |
| Monitoring `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID`, `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET` | R bootstrap identity, protect both | deploy-monitoring prompts and injects these differently named env vars; direct playbook always logs into Infisical |
| Monitoring `infisical_url`, `infisical_environment`, `infisical_secret_path`, `infisical_project_id` | O existing play vars, HTTPS/slug/path/ID, N | Playbook + .infisical.json; alternative secret delivery not implemented |
| `GRAFANA_ADMIN_PASSWORD` -> `grafana_admin_password`; `PVE_EXPORTER_TOKEN_VALUE` -> `pve_exporter_token_value`; `DISCORD_ALERT_WEBHOOK` -> `discord_alert_webhook` | All R, password/token/HTTPS webhook, S | Infisical root path -> facts -> Compose/secret file; not a DB/volume backup |
| `PVE_EXPORTER_USER` -> `pve_exporter_user`; `PVE_EXPORTER_TOKEN_NAME` -> `pve_exporter_token_name`; `PVE_EXPORTER_VERIFY_SSL` -> `pve_exporter_verify_ssl` | All R in current assertion, user@realm/name/boolean-like string; N metadata | Same lookup; exporter API access, Docker Compose host and existing monitoring network required |
| Runner `infisical_url`, `infisical_environment`, `infisical_project_id`, `infisical_secret_path`, `infisical_registry_secret_path` | O playbook defaults, N URL/slug/ID/paths | /forgejo-runner/connections and /forgejo-runner/registry; unconditional Infisical pre-tasks |
| `HOMELAB_IAC_CONNECTION_TOKEN`, `CEM_CONNECTION_TOKEN`, `CUSTOM_THEME_CONNECTION_TOKEN` -> `forgejo_runner_connection_tokens` | R per active connection, opaque S strings | Infisical; roles accept dictionary but current configure playbook has no private-source path |
| Matching `HOMELAB_IAC_CONNECTION_UUID`, `CEM_CONNECTION_UUID`, `CUSTOM_THEME_CONNECTION_UUID` -> `forgejo_runner_connection_uuids` | R, UUID identity metadata, treat private pairing with token as S | Infisical; registration must already exist; do not recreate identity during restore |
| `REGISTRY_USERNAME`, `REGISTRY_READ_TOKEN` -> `forgejo_runner_registry_username`, `forgejo_runner_registry_token` | R for active private images; username N, token S | Infisical -> root-protected registry auth; does not restore registry blobs |
| `forgejo_runner_instances`, `forgejo_runner_version`, `forgejo_runner_checksum`, `forgejo_runner_service_state`, `forgejo_runner_registry_auth_required` | O role defaults, N topology/list/version/hash/state/bool; secrets remain separate maps | [Defaults](../ansible/roles/forgejo_runner/defaults/main.yml) own all optional paths/packages/socket settings; environment-specific labels/images/URLs currently fixed defaults |
| `RUNNER_SSH_PUBLIC_KEY_FILE`, `RUNNER_SSH_PRIVATE_KEY_FILE`, `runner_management_public_key_file` | O Make defaults -> required bootstrap public-key file, path N/private bytes S | Existing SSH/Proxmox pct access; no private-key distribution; historical bootstrap requires identity review |
| `garage_version`, `garage_binary_sha256`, `garage_s3_bind` | O defaults, N version/64-hex/IP:port | Garage role, SSH/sudo; runtime RPC identity generated/preserved on host, not an operator input export |
| tfstate-configure, `TFSTATE_KNOWN_HOSTS` | Static SSH inventory + fixed PG17 config; O qualification known_hosts path, N | No Infisical login; PG peer-admin via SSH; qualification credentials disposable, not production inputs; address/TLS config not a portable variable schema |
| `k3s_version`, `k3s_sha256`, `k3s_init_host`, `k3s_pod_cidr`, `k3s_service_cidr`, `k3s_cluster_dns`, `k3s_known_networks`, `k3s_admin_cidrs`, `k3s_disable` | R profile entries, N pinned release/hash/host/CIDRs/IP/lists | [Profile](../ansible/vars/k3s-stage-a.yml) + generated applied inventory; not Infisical-dependent; other environments need reviewed profile/interface, not changed live defaults |
| `K3S_PRIVATE_DIR` / bootstrap-token | R install/snapshot; absolute private directory0700, token0600 S | Explicit controller file; no real generation/export here; same token required for matching snapshot recovery |
| `STAGE_A_ALLOCATION_REVIEWED`, `STAGE_A_APPLY_APPROVED`, `STAGE_A_PLAN_SHA256`, `STAGE_A_START_APPROVED`, `STAGE_A_CONFIGURE_APPROVED`, `K3S_TOKEN_APPROVED`, `K3S_INSTALL_APPROVED`, `K3S_SNAPSHOT_APPROVED`, `CONTROLLER_ALLOCATION_REVIEWED`, `CONTROLLER_APPLY_APPROVED` | R per corresponding guarded action, `yes` or reviewed SHA256, N | Explicit Make inputs; flags do not replace operator review. Preserve all guards in future adapters |

Workstation host baseline and generic guest roles also consume tracked inventory
and host-specific vars under ansible/inventories; these encode real mappings,
not portable defaults. Static tfstate/Garage/runner inventories and monitoring
Compose endpoints similarly need scoped parameterization before external-user
deployment can be claimed. No Kubernetes app/CSI input interface exists yet.

## Smallest proposed adapter (Task045, not implemented)

Start with Stage A, not every wrapper: one explicit Make input-source selector
(name to be chosen in045) routes either existing Universal Auth or a deliberately
supplied private provider environment into the same guarded commands. Keep native
terraform.tfvars/image/server map; expose the existing module's `ssh_public_key`
at the root with backwards-compatible operator default. Validate missing inputs
before execution, no credential fallback and no changes to state authority.
Do not make callers copy/edit a public key owned by another person. A small
private file may name non-secret profile paths, not re-encode every Terraform
field or hold command-line secrets. Add only if it removes demonstrated friction.
Later runner/monitoring adapters normalize inputs into the existing facts/role
variables, preserving no_log and least privilege; do not duplicate playbooks.

## Safe kit specifications (not executable interfaces)

Starter: public code/locks/runbook + documented hypervisor/network/storage
prerequisites + one selected stack's non-secret example profile + privately
supplied credentials/public SSH key. Explicitly new identity/state/data; no
original operator secrets, historical states or recovery payloads. Current
operator-specific roots cannot yet fulfill this whole workflow unchanged.

Recovery: exact code/tool versions + reviewed authoritative state/input generation
+ trust/access + matching snapshot/server-token when preserving K3s identity
+ compatible DB/files/encryption identity or independently retrievable protected
backup references. Inventory missing items as BLOCKED, never fresh fallback.
Bulk media need not be in the kit, but required referenced bytes must be
recoverable. See the [reconciled recovery contract](recovery-contract.md).
Project produces usable contents and instructions; operator protects iCloud or
other chosen external storage. No real kit, secrets or data captured here.
