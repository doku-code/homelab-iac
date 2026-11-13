---
id: INV-pve-management-bootstrap
title: pve-management bootstrap — readiness and implementation plan
summary: Readiness, exact API privileges, SSH/TLS/state decisions, proposed VM values and the next step for provisioning mgmt-control-01 on pve-management; nothing applied.
type: investigation
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [investigation, bootstrap, pve-management, plan]
component: pve-management
topics: [opentofu, bpg-proxmox, cloud-init, api-token, tls, state, sops]
related_tasks: [TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012]
related: [ARCH-platform, ADR-002, ADR-003, ADR-004, ADR-008, M001]
---

# pve-management bootstrap — readiness and implementation plan

## Question

What is needed to provision and configure `mgmt-control-01` on `pve-management` from the operator
workstation (ADR-008), and what is ready now?

## Method

Repository review and offline implementation at 2026-11-12; read-only, unauthenticated checks of
`pve-management` (TCP 8006/22, TLS handshake, SSH host-key scan). No API call, no login, no plan, no apply.

## Findings

### Implementation (offline, in the repository)

| Piece | Path | Status |
|-------|------|--------|
| OpenTofu root (reuses `terraform/modules/headless-vm`) | `terraform/stacks/pve-management-control/` | Written; `tofu validate` and 5 mocked `tofu test` runs pass |
| Module made engine-agnostic (no `required_version`; `username`, `started`, `on_boot` variables, legacy defaults) | `terraform/modules/headless-vm/` | Legacy roots unchanged: Terraform mocked tests 13/13 pass |
| Auth guard (token only, no `root@pam`, no password, TLS on, no debug logs) | `scripts/pve-auth-guard.py` | Offline tests pass |
| Read-only discovery incl. effective token privileges | `scripts/pve-discover.py`, `make mgmt-discover` | Logic tested offline; not run live (no token yet) |
| Make workflow | `mgmt-check`, `mgmt-discover`, `mgmt-plan`, `mgmt-apply`, `mgmt-configure`, `mgmt-state-backup` | Refusal paths tested in a sandbox |
| Ansible baseline (Ubuntu, OpenTofu 1.13.9, SOPS, age, guest agent, SSH hardening; no runner) | `ansible/playbooks/configure-mgmt-control.yml` | Syntax check passes |
| CI | `.forgejo/workflows/validate.yml` step "Validate OpenTofu root …" (pinned OpenTofu, `make mgmt-check`) | Not yet run in CI |
| Runbook | [root README](../../terraform/stacks/pve-management-control/README.md) | Written |

### OpenTofu compatibility

OpenTofu 1.13.9 installs `bpg/proxmox` 0.112.0 (signed) and validates the reused module once its
Terraform-specific `required_version` is removed from the module (roots keep their own). The new root
has its own OpenTofu lock file (linux_amd64, darwin_arm64, darwin_amd64). Legacy roots stay on Terraform.
Difference handled in tests: OpenTofu mocks generate computed IDs at plan time, so the test gives the
image a realistic volume ID. A provider deprecation warning (`timeout_move_disk`) comes from the module
output and is harmless.

### Proxmox API privileges (exact, from the PVE API schema)

Dedicated user `tofu@pve` with a privilege-separated token. Minimum role and ACL paths:

| Path | Privileges | Needed for |
|------|-----------|------------|
| `/vms` | `VM.Allocate VM.Audit VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.PowerMgmt VM.GuestAgent.Audit` | Create/configure/start the VM, cloud-init drive, read agent addresses |
| `/storage/<image datastore>` | `Datastore.AllocateTemplate Datastore.Audit` | `download-url` of the cloud image into `import` content |
| `/storage/<disk datastore>` | `Datastore.AllocateSpace Datastore.Audit` | Disk and cloud-init volume allocation |
| `/nodes/pve-management` | `Sys.AccessNetwork Sys.Audit` | `download-url` (instead of `Sys.Modify` on `/`), task status |
| `/sdn/zones/localnetwork/<bridge>` | `SDN.Use` | Attaching the NIC to the bridge |

No Administrator role, no `Sys.Modify` on `/`, no realm/user privileges. Commands for the operator
(on `pve-management`, after confirming storage and bridge names):

```
pveum role add IaCManagementVM -privs "VM.Allocate VM.Audit VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.PowerMgmt VM.GuestAgent.Audit Datastore.AllocateTemplate Datastore.AllocateSpace Datastore.Audit Sys.AccessNetwork Sys.Audit SDN.Use"
pveum user add tofu@pve --comment "OpenTofu automation for pve-management"
pveum user token add tofu@pve mgmt --privsep 1
# Same ACL for the user and the token; one line per path in the table above, e.g.:
pveum acl modify /vms --roles IaCManagementVM --users tofu@pve --tokens 'tofu@pve!mgmt'
```

The single role is assigned on each path; privileges a path does not check are inert there, and
nothing is granted on `/`. `VM.GuestAgent.Audit` exists from PVE 9.0 (on 8.x the agent read uses
`VM.Monitor`); `make mgmt-discover` reports the PVE version and any missing privilege per path. Unverified until the first plan/apply: whether importing from
an `import` volume needs more than `Datastore.Audit` on the image storage.

### SSH

Not required for provisioning: the `bpg/proxmox` v0.112.0 documentation lists SSH only for snippets,
some file uploads, `source_file.path` imports and container idmaps; `import_from` and image downloads
use the API. The provider block has no SSH settings. SSH is used only by Ansible into the VM, with the
repository operator key (`keys/doku-lab-admin.pub`) injected by cloud-init.

### TLS (observed 2026-11-12)

- `pve-management:8006` presents the default node certificate issued on 2026-11-11 by the host's own
  `PVE Cluster Manager CA` (valid to 2028-11-10); SANs: `192.168.0.10`, `pve-management`,
  `pve-management.doku-lab.net`, localhost. Leaf SHA-256 fingerprint
  `FC:BE:8F:18:57:93:1F:AD:34:E9:2B:43:4A:C5:A9:8D:D0:36:77:7C:50:63:79:49:F4:8D:85:63:D3:9F:9B:91`.
- Not trusted by the workstation yet (expected). The root never sets `insecure = true`.
- **Bootstrap strategy:** trust the host's `pve-root-ca.pem` on the workstation (macOS Keychain, since
  OpenTofu uses the system store), after verifying it on the console. `mgmt-discover` also accepts `PVE_CA_FILE`.
- **Later:** an ACME certificate for `pve-management.doku-lab.net` (DNS-01) removes CA distribution;
  it needs DNS API credentials and is a separate, approved change.

### SSH host keys

The workstation's `known_hosts` entries for `192.168.0.10` are the retired `pve-infra` keys; none
match the keys `pve-management` presents (ED25519 `SHA256:gdWdOeB7oxmR5xMQ2C/KjjgOW5hZDOxw46LnB1I6mgY`).
SSH therefore fails closed. The operator replaces them after checking the fingerprints on the console.

### State

- **Now:** local backend in the root directory on the workstation (git-ignored), one operator; after each
  apply `make mgmt-state-backup` writes a dated, age-encrypted copy to an off-machine location.
  Never stored on `pve-management` or the VM it manages. Restore = decrypt + no-change plan.
- **Later (TASK-010):** a shared remote backend with locking before any second executor may apply. Not now.

### Secrets

The API token comes from Infisical, path `/pve-management` (`MGMT_INPUT_SOURCE=infisical`), or from the
environment (`MGMT_INPUT_SOURCE=env`, e.g. decrypted from SOPS during recovery). No default, no fallback.
The guard strips Infisical bootstrap credentials before OpenTofu runs. SOPS + age files follow in TASK-011.

### Proposed VM configuration (not confirmed)

| Value | Proposed | Confirm with |
|-------|----------|--------------|
| VMID | 100 | `mgmt-discover` (used VMIDs, next free) |
| Address | static, outside the DHCP pool (e.g. a reserved `192.168.0.x/24`) | pfSense DHCP scope |
| Gateway / DNS | `192.168.0.1` / `192.168.0.20` | pfSense, AdGuard |
| vCPU / RAM / disk | 2 / 4096 MiB / 40 GiB | `pve-management` capacity |
| Image storage / disk storage / bridge | `local` (needs `import` content) / `local-lvm` / `vmbr0` | `mgmt-discover` |
| Ubuntu | 24.04 LTS cloud image, dated release + SHA256 | cloud-images.ubuntu.com SHA256SUMS |

## Inferences

- Everything up to the first read-only API call is ready; every remaining step needs an operator action.
- The legacy roots that still point at `192.168.0.10` are blocked by a Make guard; their correct
  endpoint is an operator decision ([INV-legacy-inventory](legacy-inventory.md)).

### Acceptance tests for M001

| Level | Test |
|-------|------|
| Offline (CI) | `make mgmt-check`: fmt, validate, 5 mocked `tofu test` runs, Ansible syntax, guard tests |
| Live read-only | `mgmt-discover`: TLS verified, standalone, storages with `import`, bridge, free VMID, no missing privileges |
| Live change (approved) | Plan shows exactly 1 image download + 1 VM; apply; VM boots; SSH works; second plan reports no changes |
| Configuration | `mgmt-configure` twice, second run without changes; tool versions reported |
| Recovery | State restored from the age backup gives a no-change plan; plan runs with `MGMT_INPUT_SOURCE=env` |

## Open questions

- Operator: create the identity/token and store it; trust the PVE CA; replace stale host keys.
- Operator: confirm the VM address and sizing; whether `local` should get the `import` content type.
- Correct API endpoint for the four legacy roots that still use `192.168.0.10`.
