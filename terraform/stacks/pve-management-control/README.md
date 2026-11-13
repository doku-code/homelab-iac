# pve-management-control — management VM `mgmt-control-01`

OpenTofu root (ADR-003) that creates the Ubuntu management VM on the standalone `pve-management`
host, reusing `terraform/modules/headless-vm`. Configuration is
`ansible/playbooks/configure-mgmt-control.yml`. Plan, decisions and acceptance tests:
[INV-pve-management-bootstrap](../../../docs/investigations/pve-management-bootstrap.md).

Runs **only from the operator workstation** (ADR-008). CT301 never receives these credentials.

## Prerequisites (operator)

1. OpenTofu 1.13.9 (`brew install opentofu`), Python controller environment (`make setup-controller`).
2. TLS trust for the `pve-management` certificate: add the host's `pve-root-ca.pem` to the workstation
   trust store (macOS Keychain, "Always Trust" for SSL), after checking its fingerprint on the host console.
   `PVE_CA_FILE` is honoured by `mgmt-discover` only; OpenTofu uses the system store.
3. A dedicated API identity and token (exact privileges in the investigation document), stored in
   Infisical under `/pve-management` as `PROXMOX_VE_API_TOKEN`, or exported for `MGMT_INPUT_SOURCE=env`.
4. The SSH host key of `pve-management` verified on the console; stale `pve-infra` entries for
   192.168.0.10 removed from `known_hosts` by the operator.

## Workflow

| Step | Command | Effect |
|------|---------|--------|
| Offline check | `make mgmt-check` | fmt, validate, mocked `tofu test`, Ansible syntax, guard tests |
| Discovery | `make mgmt-discover MGMT_INPUT_SOURCE=infisical MGMT_DISCOVER_ARGS="--image-datastore … --disk-datastore … --bridge …"` | Read-only GETs: version, standalone status, storages, bridges, used VMIDs, token privileges |
| Profile | copy `terraform.tfvars.example` to `terraform.tfvars` | Replace every PROPOSED value with discovered/confirmed values |
| Plan | `make mgmt-plan MGMT_ALLOCATION_REVIEWED=yes MGMT_INPUT_SOURCE=infisical` | Saved plan `mgmt.tfplan` + SHA256; expected: 1 image download, 1 VM, nothing else |
| Apply | `make mgmt-apply MGMT_APPLY_APPROVED=yes MGMT_PLAN_SHA256=<sha> MGMT_INPUT_SOURCE=infisical` | **Mutates pve-management.** Applies exactly the reviewed plan |
| Backup | `make mgmt-state-backup MGMT_BACKUP_DIR=<off-machine dir> AGE_RECIPIENTS_FILE=<recipients>` | age-encrypted, dated copy of the state |
| Configure | `make mgmt-configure MGMT_CONFIGURE_APPROVED=yes MGMT_SOURCE_COMMIT=<full sha on the GitHub mirror>` | Ansible baseline and toolchain |
| Idempotency | `make mgmt-plan …` again | Must report no changes |

## State

Local backend: `terraform.tfstate` beside this file on the operator workstation (git-ignored), one
operator at a time (OpenTofu's local lock file guards concurrent runs on that machine). After every
apply, run `mgmt-state-backup` to an off-machine location. Restore = decrypt the latest `.tfstate.age`
into this directory and confirm `make mgmt-plan` reports no changes. A shared remote backend with
locking is required before any second executor (runner) may apply (TASK-010).
