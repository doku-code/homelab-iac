---
id: TASK-014
title: Bootstrap deployment runner VM on pve-core
summary: Runner VM deploy-runner-01 (VMID 302, .32) on pve-core via headless-vm, deploy_runner role, main-only wrapper, approval-gated dispatch workflow and a disposable proof root (ADR-014).
type: task
status: in-progress
priority: high
milestone: M003
created: 2026-11-17
updated: 2026-11-17
tags: [runner, forgejo, opentofu, ansible, ci]
depends_on: []
related: [ARCH-platform, INV-new-proxmox-cluster-inventory, GUIDE-handoff]
related_decisions: [ADR-014, ADR-008, ADR-003]
related_implementations: [terraform/stacks/deploy-runner, terraform/stacks/ci-disposable, ansible/roles/deploy_runner, ansible/playbooks/configure-deploy-runner.yml, .forgejo/workflows/deploy.yml, Makefile]
related_tests: [tests/deploy-runner.py, terraform/stacks/deploy-runner/tests/runner.tftest.hcl, terraform/stacks/ci-disposable/tests/probe.tftest.hcl]
tests_justification: ""
verification_commands: [make deploy-runner-check]
evidence: []
---

# TASK-014 — Bootstrap deployment runner VM on pve-core

**Authorization:** LIVE_CHANGE with approval. Every apply, credential creation and runner registration needs
the operator's explicit approval for that operation; a task status never authorizes one.

## Goal

A dedicated, OpenTofu-built and Ansible-configured runner executes approved infrastructure workflows from
the existing Forgejo with scoped credentials; CT301 stays validation-only (ADR-014).

## Context

- [ADR-014](../docs/decisions/ADR-014-dedicated-forgejo-deployment-runner.md), [ADR-008](../docs/decisions/ADR-008-workstation-bootstrap-ct301-validation-only.md)
- Reused: `terraform/modules/headless-vm`, the `pve-management-control` Make gates (`MGMT_RUN`, saved plan +
  SHA256), the CT301 `forgejo_runner` binary pin and `server.connections` registration

## Design (operator decisions 2026-11-17)

- **Placement:** `pve-core` (operator, 2026-11-17: first `pve-management`, then moved because 2 vCPU / 2 GiB
  was far too small and `pve-management` had only ~3.7 GiB free), VMID 302, `192.168.0.32/24` (no ping/ARP
  reply, VMID free), Debian 13 cloud image, **6 vCPU / 8 GiB** / 24 GiB thin (pve-core: 16 CPUs, ~29.6 GiB free).
- **VM root** `terraform/stacks/deploy-runner` (`headless-vm` module), applied from the workstation with the
  existing `tofu@pve!mgmt` token through `deploy-runner-plan/apply` (saved plan + SHA256, state guard); the
  token needs one more ACL, `IaCManagementVM` on `/nodes/pve-core` (operator-approved privilege change).
- **Role** `deploy_runner`: forgejo-runner 13.0.0 (same pin as CT301), host-mode label `homelab-deploy`,
  repository-scoped registration (UUID/token in `server.connections`), capacity 1; OpenTofu 1.13.9 pinned.
- **Ref gate:** job user `runner` has no credentials; sudo allows only `/usr/local/sbin/homelab-deploy` as
  `deploy`, which clones Forgejo `main` afresh per run (Git config/hooks off, empty HOME, root-owned tofu CLI
  config), plans only the current `main` tip of an allowlisted root, and applies only an unexpired saved
  plan from its own commit.
- **Approval outside the job:** `make deploy-runner-review` shows the plan on the runner over SSH;
  `make deploy-runner-approve` writes the root-owned `approvals/<root>.sha256` that `apply` requires. Jobs
  can trigger an apply, never approve one (review finding 2026-11-17: job logs are public and forgeable).
- **Workflow** `deploy.yml`: `workflow_dispatch` only, `main` + `vars.DEPLOY_RUNNER_APPROVED`, no secrets.
- **Proof root** `terraform/stacks/ci-disposable`: one stopped 1 GiB, NIC-less VM 9900 on `pve-core` in pool
  `ci-disposable`; state local to the runner (first answer to ADR-014's state question: runner-only roots
  keep their state on the runner, one writer; shared roots still wait for TASK-010).
- **Credentials:** `deploy-runner@pve!ci` scoped to `/pool/ci-disposable`, `/storage/local-lvm`,
  `/nodes/pve-core`; Forgejo runner UUID/token; both in Infisical `/deploy-runner`. CT301 gets none.

Runbook and exact commands: [terraform/stacks/deploy-runner/README.md](../terraform/stacks/deploy-runner/README.md).

## Acceptance criteria

- [x] Offline: both roots fmt/validate/mocked tests; playbook syntax; wrapper, role, workflow and Make guard tests
- [x] Reviewed `deploy-runner-plan` (creates only the image download and VM 302) approved by the operator
- [x] VM applied
- [x] `deploy-runner-configure` converges, second run changed=0
- [x] Runner online in Forgejo with label `homelab-deploy`, repository scope only
- [ ] Dispatch `ci-disposable` plan → apply with the approved SHA256 creates VM 9900; plan-destroy → apply removes it
- [ ] A dispatch from a non-main commit is refused by the wrapper; validation jobs never receive deployment credentials

## Verification

```
make deploy-runner-check
infisical run --silent --env dev --path /pve-management -- make deploy-runner-plan MGMT_INPUT_SOURCE=env DEPLOY_RUNNER_ALLOCATION_REVIEWED=yes DEPLOY_RUNNER_NEW_STATE=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/deploy-runner.py` | wrapper end to end (local Git remote, fake tofu): branch commits refused, wrong/replayed plan hash refused, credentials only for plan/apply; role no_log and file modes; sudoers single rule; workflow boundary; Make guards | `make deploy-runner-check` | PASS 2026-11-17 |
| `terraform/stacks/deploy-runner/tests/runner.tftest.hcl` | placement, sizing, image pin, cloud-init key, old-environment and node/VMID refusals | `make deploy-runner-check` | PASS (3) 2026-11-17 |
| `terraform/stacks/ci-disposable/tests/probe.tftest.hcl` | probe stays stopped, tiny, NIC-less, in the pool and VMID range | `make deploy-runner-check` | PASS (3) 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Read-only allocation | .32 no reply, VMID 302 free (only VM 100 in doku-lab), pve-management 3.7 GiB available, thin pool 16 % | `ping`, `ip neigh`, `pvesh get /cluster/resources`, `free -m` | 2026-11-17 |
| Existing token scope | `tofu@pve` + `!mgmt` hold IaCManagementVM on `/vms` (all VMs, not only VM 100), `/storage/local`, `/storage/local-lvm`, `/nodes/pve-management`, vmbr0; nothing on `/nodes/pve-core` | `pveum acl list` | 2026-11-17 |
| Offline checks | PASS | `make deploy-runner-check`, `scripts/check-quality.py` | 2026-11-17 |
| Independent review (harness-code-reviewer) | 2 major + 5 minor found; fixed: out-of-band approval file, plan only at main tip, fresh clone + Git/tofu/Python isolation, 24 h plan expiry, lock inherited by children, restart refused under a held lock, tests for template, force-push, lock, credentials | tests/deploy-runner.py | 2026-11-17 |
| State continuity (`pve-management-control`) | No changes (ISO + VM 100 refreshed) | `make mgmt-plan`, plan SHA256 `0dfee99e…0600d` | 2026-11-17 |
| Runner plan (first, pve-management) | 2 to add: image download and VM 302 with 2 vCPU / 2048 MiB; operator rejected the sizing and moved the runner to pve-core with 6 vCPU / 8 GiB. Superseded, not applied | `make deploy-runner-plan`, SHA256 `ee3a09fc…d4ffc` | 2026-11-17 |
| Token ACL for pve-core (operator-approved) | `pveum acl modify /nodes/pve-core --roles IaCManagementVM` for `tofu@pve` and `tofu@pve!mgmt`; listed afterwards | `pveum acl list` on 192.168.0.11 | 2026-11-17 |
| Runner plan (pve-core) | 2 to add, 0 change, 0 destroy: image download to pve-core `local` (import, sha512) and VM 302 `deploy-runner-01` on pve-core, 6 vCPU, 8192 MiB, 24 GiB `local-lvm`, 192.168.0.32/24; approved by the operator | `make deploy-runner-plan`, SHA256 `a3d3cc1be32bfb0f65c63dbaaf3130f423e3a393eb4bc5214e34b7bdb68f382a` | 2026-11-17 |
| Runner apply | Apply complete: 2 added, 0 changed, 0 destroyed; VM 302 running, answers ping; state `terraform/stacks/deploy-runner/terraform.tfstate` (0600, git-ignored, this workstation only). Warning: QEMU agent timeout (15 min): the Debian generic cloud image has no `qemu-guest-agent` until `headless_baseline` installs it | `make deploy-runner-apply` | 2026-11-17 |
| DHCP range | Operator: pfSense DHCP pool is 192.168.0.100–.200, so static .32 is outside it | operator statement | 2026-11-17 |
| SSH host key | ED25519 `SHA256:uWRZqqgqUdqahMNjZJLpU6f7AOBAI+yTK3w/M+3noj8` from `ssh-keyscan`; matches the key read out-of-band from VM 302's disk on pve-core (read-only loop device + `debugfs -c`); pinned in `~/.ssh/known_hosts` | `ssh-keyscan`, `debugfs` | 2026-11-17 |
| Runner credentials (operator-authorized) | Pool `ci-disposable`, role `IaCDisposable`, user `deploy-runner@pve`, token `!ci` (privsep) with ACLs on `/pool/ci-disposable`, `/storage/local-lvm`, `/nodes/pve-core`; Forgejo repository runner id 10 `deploy-runner-01` created through the API; the three values stored in Infisical `dev:/deploy-runner`, no local copy | `pveum acl list`, Forgejo API, `infisical run` (lengths only) | 2026-11-17 |
| Configure | Run 1: ok=30 changed=25 failed=0; run 2: ok=26 changed=0 failed=0 | `make deploy-runner-configure` | 2026-11-17 |
| Runner state | `forgejo-runner` and `qemu-guest-agent` active; Forgejo shows `deploy-runner-01` v13.0.0, labels `[homelab-deploy]`, idle; config 0640 root:runner, proxmox.env 0640 root:deploy (runner cannot read it), sudo for `runner`: only `(deploy) /usr/local/sbin/homelab-deploy`; OpenTofu 1.13.9 | `systemctl`, Forgejo API, `stat`, `sudo -l` | 2026-11-17 |
| VM state after configure | No changes | `make deploy-runner-plan` | 2026-11-17 |
| Dispatch plan (`DEPLOY_RUNNER_APPROVED=true` set) | Run 84 success on `8c03161`; review on the runner: 1 to add, VM 9900 on pve-core, pool `ci-disposable`, stopped, 128 MiB, 1 GiB, no NIC; PLAN_SHA256 `1d20ed019935bf1f003f8d12d2e87f75c240ab4e4162efe049a72c1c4c52497d` | Forgejo Actions run 84, `make deploy-runner-review` | 2026-11-17 |
| Boundary as job user `runner` | Refused: older main commit `35f448d`, foreign commit, short commit, wrong plan SHA256, correct SHA256 without operator approval; `sudo` to root or to any other command as `deploy` asks for a password | `sudo -u runner sudo -n -u deploy homelab-deploy …` over SSH | 2026-11-17 |

## Completion summary

_Not completed._
