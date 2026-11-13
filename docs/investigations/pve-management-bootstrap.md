---
id: INV-pve-management-bootstrap
title: pve-management bootstrap — readiness and implementation plan
summary: Reusable IaC, missing prerequisites, task sequence and acceptance tests for provisioning the management VM on pve-management; plan only.
type: investigation
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-12
tags: [investigation, bootstrap, pve-management, plan]
component: pve-management
topics: [opentofu, bpg-proxmox, cloud-init, api-token, runner, state, sops]
related_tasks: [TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012]
related: [ARCH-platform, ADR-002, ADR-003, ADR-004, M001]
---

# pve-management bootstrap — readiness and implementation plan

## Question

What exactly is needed to provision and configure the Ubuntu management VM on `pve-management`
from the existing infrastructure, without applying anything yet?

## Method

Read-only review of the repository at `51a4d6e` (2026-11-12): Terraform modules/stacks, Make
targets, Ansible playbooks/roles, CI workflows, and the unfinished Codex runner work kept in
`stash@{0}`. No live system was contacted.

## Findings

### Reusable IaC

| Asset | What it gives | Reuse |
|-------|---------------|-------|
| `terraform/modules/headless-vm` | VM from an imported cloud image (`import_from`), cloud-init IP/DNS/user/SSH key, profile object input | Port to `modules/opentofu/proxmox-vm` (Ubuntu, OpenTofu) |
| `terraform/stacks/pve-lab-controller` | Checksum-pinned image download (`proxmox_download_file`, content `import`) + VM; mock-provider tests | Template for `stacks/management/mgmt-vm` |
| `tests/vm-profiles.py`, `*.tftest.hcl` with `mock_provider` | Offline plan tests without Proxmox | Same pattern with `tofu test` |
| Make `controller-plan` / `controller-apply` | Saved plan + explicit approval variable + apply of that exact plan | Same flow for `mgmt-plan` / `mgmt-apply` |
| `ansible/playbooks/configure-recovery-controller.yml` | Pinned IaC toolchain install, repo checkout from an independent source | Base of the management VM role (switch to Ubuntu + OpenTofu) |
| `ansible/roles/guest_base`, `headless_baseline` | Baseline OS configuration | Review, reuse what is OS-agnostic |
| `ansible/roles/forgejo_runner` (+ unfinished VM208 "infra runner" in `stash@{0}`) | Runner install/registration | Reference for a dedicated management runner |
| `keys/doku-lab-admin.pub` | Operator public SSH key | Cloud-init authorized key |

Pins today: `bpg/proxmox` 0.112.0, Terraform `>= 1.16.0`. New OpenTofu roots set their own
`required_version` and lock file (the legacy constraint does not apply to OpenTofu).

### Runner capabilities and network

- The only runner, CT301 (`homelab-iac` label), runs validation only, gated by
  `CI_QUALITY_APPROVED` on pushes to `main`. It has a rootful Podman socket; the legacy trust
  review is unresolved, so it must not hold Proxmox credentials.
- No workflow plans or applies infrastructure; every legacy apply was operator-run via Make.
- Network reachability from CT301 or the workstation to `pve-management` (8006/tcp, 22/tcp) is unverified.

### Proxmox API authentication

- Not created or verified. Required: a dedicated user (e.g. `tofu@pve`), a custom role with the
  minimum VM lifecycle, datastore, image download and network-use privileges for the installed
  PVE version, and a privilege-separated API token (`PROXMOX_VE_API_TOKEN=user@realm!id=secret`).
- Legacy flows partly use the `root@pam` password; the new root must reject password auth (the
  Stage A input check already does this) and use the token only.
- TLS: legacy examples set `insecure = true`. The target verifies TLS (pinned PVE CA or a
  trusted certificate on `pve-management`); decide which.

### SSH

- VM creation needs no SSH to the hypervisor if cloud-init stays API-driven (no snippets).
- The management VM gets the operator key and a dedicated automation key via cloud-init for Ansible.
- Hypervisor SSH stays an administrator path, not an automation dependency.

### Image and cloud-init

- No VM template is needed: download a SHA256-pinned Ubuntu LTS cloud image into a datastore
  with the `import` content type enabled, import it as the boot disk, cloud-init for user/key/IP.
- To verify on `pve-management`: storage names and content types, bridge, free VMID, the IP
  address (static reservation or DHCP), and that the guest agent is installed by Ansible.

### State storage

- Legacy state is local and unbacked. The first new root must not keep state only on one laptop,
  and must not store it on the VM it creates.
- Smallest safe option: local state on the operator workstation, OpenTofu client-side state
  encryption, and an encrypted off-host copy after each apply; a shared backend is decided in
  TASK-010 before more roots depend on it.

### Secrets bootstrap

- The token can be supplied from Infisical (working today, existing `INFISICAL_RUN` pattern) or
  from a SOPS + age file (TASK-011). The input source is explicit; there is no fallback between them.
- M001 is complete only when SOPS + age covers the bootstrap credentials and a workstation can
  run the plan with Infisical unavailable.

### Recovery

- The management VM is rebuildable: its definition is the root plus the Ansible role; its
  irreplaceable inputs (state, token, age key) live off the VM. A PBS backup is a convenience,
  not the recovery method.

## Inferences

- **Contradiction with the briefing:** "use the existing CI runners to provision `pve-management`"
  is not possible safely today. The existing infrastructure contributes Forgejo (code), Infisical
  (token), the controller environment and the Make workflows; the first apply runs from the operator
  workstation, which is also the disaster-recovery path. CI-triggered plans follow once the
  management VM hosts its own trusted runner (TASK-009).
- Bootstrapping `pve-management` needs only the `pve-management` facts from M000 (TASK-007
  checks them), not the full inventory; M000 and M001 can progress in parallel.

### Proposed sequence

1. **TASK-007** — operator creates the user/role/token; agent verifies read-only: API version and
   node list with the token, TLS, storages and `import` content, bridge, free VMID/IP, reachability.
2. **TASK-006** — target layout, pinned OpenTofu in the controller setup, `mgmt-*` Make targets.
3. **TASK-008** — `modules/opentofu/proxmox-vm` + `stacks/management/mgmt-vm` with `tofu test`
   (mock provider); a reviewed plan; apply only after approval.
4. **TASK-010** (state decision for this root) before that apply.
5. **TASK-009** — Ansible baseline: users, SSH hardening, guest agent, OpenTofu, Ansible, SOPS/age,
   Phase CLI later; dedicated runner registration.
6. **TASK-011** — SOPS + age for the token and SSH material; **TASK-012** — workstation runbook, exercised once.

### Minimal acceptance tests

| Level | Test |
|-------|------|
| Offline (CI) | `tofu fmt -check`, `tofu validate`, `tofu test` with mock provider (node is `pve-management`, image checksum set, no password auth), Ansible `--syntax-check` |
| Live read-only | Token reads `/version` and `/nodes`; TLS verified; required storages and bridge exist |
| Live change (approved) | Plan shows only the image download and one VM; apply succeeds; VM boots and answers SSH; second plan reports no changes |
| Configuration | Ansible converges twice with `changed=0` the second time; tool versions match pins; runner registered and runs a harmless job |
| Recovery | From a workstation, with the SOPS file and age key, the plan runs without Infisical |

## Open questions

Needed from the operator before any provisioning:

- First execution path: workstation via Make (recommended) or a dedicated workflow on CT301.
- Management VM: VMID, address (static or DHCP reservation), vCPU/RAM/disk, Ubuntu LTS version.
- `pve-management` storage for images/disks and the bridge to use.
- TLS approach for the Proxmox API (pinned CA vs trusted certificate).
- Token source for the first run (Infisical now, SOPS from TASK-011) and age key custody.
