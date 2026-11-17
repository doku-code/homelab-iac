---
id: TASK-015
title: "k3s cluster on doku-lab: first server on pve-lab"
summary: terraform/stacks/k3s VMs (for_each, rebuildable), k3s role with embedded etcd, token in Infisical /k3s, host keys pinned out-of-band, workstation kubeconfig (ADR-011).
type: task
status: in-progress
priority: high
milestone: M004
created: 2026-11-17
updated: 2026-11-17
tags: [k3s, opentofu, ansible]
depends_on: []
related: [ARCH-platform, INV-new-proxmox-cluster-inventory, GUIDE-handoff]
related_decisions: [ADR-011, ADR-012, ADR-008, ADR-003]
related_implementations: [terraform/stacks/k3s, ansible/roles/k3s, ansible/playbooks/configure-k3s.yml, scripts/pin-guest-hostkey.sh, Makefile]
related_tests: [tests/k3s-cluster.py, terraform/stacks/k3s/tests/k3s.tftest.hcl]
tests_justification: ""
verification_commands: [make k3s-cluster-check]
evidence: []
---

# TASK-015 — k3s cluster on doku-lab: first server on pve-lab

**Authorization:** operator granted standing autonomy for goal-directed work on 2026-11-17; Claude Code still
asks the operator for credential and privilege changes (ACL, Infisical secret).

## Goal

M004: the first k3s cluster (embedded etcd, ready for more servers) is provisioned with OpenTofu, configured
with Ansible and reachable with kubectl from the workstation; a node can be rebuilt from IaC.

## Context

- [ADR-011](../docs/decisions/ADR-011-k3s-first-argocd-headlamp.md) (k3s, embedded etcd), [ADR-012](../docs/decisions/ADR-012-external-nvme-storage-truenas-backups.md) (no data on VM disks)
- Reused: the deploy-runner Make gates (saved plan + SHA256, state guard), the Debian 13 image pin, the k3s
  pin `v1.35.8+k3s1` from the legacy Stage A role; the legacy role/playbooks stay untouched (old lab only)

## Design

- **VMs** `terraform/stacks/k3s`: one VM per `nodes` entry (`for_each`), image per hosting Proxmox node,
  no `prevent_destroy` (cattle; rebuild with `K3S_CLUSTER_REPLACE=<name>`), agent timeout 2 min. Allowed:
  pve-core/pve-infra/pve-lab, VMIDs 310–349, 192.168.0.40–49. First: `k3s-server-01`, VM 310, pve-lab,
  192.168.0.40, 6 vCPU / 12 GiB / 64 GiB (pve-lab: 16 threads, ~26 GiB free, empty 403 GiB thin pool).
- **k3s** role `k3s`: pinned binary (SHA256, no install script), embedded etcd (`cluster-init` on the first
  server, later servers join its API), token from Infisical `dev:/k3s` (`K3S_TOKEN`, 0600 config, no_log),
  servers converge one at a time. Ingress/LB decision: keep bundled Traefik and ServiceLB for now;
  cluster/service CIDRs 10.42/16, 10.43/16 (no overlap with the LAN).
- **Host keys**: `scripts/pin-guest-hostkey.sh` pins a VM's key only when ssh-keyscan and the key read
  from the VM's own disk (read-only loop + debugfs on the Proxmox node) agree; needed because a rebuilt VM
  has a new key.
- **Access**: admin kubeconfig written to the workstation `~/.kube/config` (0600, API by IP, context
  `doku-lab`). The runner's kubeconfig waits until the runner deploys to k3s (scoped RBAC, M005/M009).

## Acceptance criteria

- [x] Offline: root fmt/validate/mocked tests (5); playbook syntax; role/template/kubeconfig/Make guard tests
- [ ] `tofu@pve!mgmt` may place VMs on pve-lab (ACL `/nodes/pve-lab`) and `K3S_TOKEN` exists in Infisical
- [ ] Plan (image + VM 310 only) applied; host key pinned out-of-band; configure converges, second run changed=0
- [ ] `kubectl get nodes` from the workstation: `k3s-server-01` Ready (control-plane, etcd)
- [ ] Rebuild from IaC: replace VM 310, re-pin, configure → node Ready again

## Verification

```
make k3s-cluster-check
infisical run --silent --env dev --path /pve-management -- make k3s-cluster-plan MGMT_INPUT_SOURCE=env K3S_CLUSTER_ALLOCATION_REVIEWED=yes [K3S_CLUSTER_NEW_STATE=yes | K3S_CLUSTER_REPLACE=k3s-server-01]
infisical run --silent --env dev --path /pve-management -- make k3s-cluster-apply MGMT_INPUT_SOURCE=env K3S_CLUSTER_APPLY_APPROVED=yes K3S_CLUSTER_PLAN_SHA256=<sha>
make k3s-cluster-hostkeys
infisical run --silent --env dev --path /k3s -- make k3s-cluster-configure K3S_CLUSTER_CONFIGURE_APPROVED=yes
kubectl get nodes -o wide
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `terraform/stacks/k3s/tests/k3s.tftest.hcl` | first-server contract, one image per Proxmox node, init node, refusals (.14, pve-management, DHCP range, CI VMIDs, no server) | `make k3s-cluster-check` | PASS (5) 2026-11-17 |
| `tests/k3s-cluster.py` | config for init/join/agent, unit, pinned binary, no_log, kubeconfig hand-off, host-key script refusals, Make guards (state, replace name, approvals, token) | `make k3s-cluster-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Read-only allocation | .40–.45 no ping/ARP reply; VMIDs in use: 100, 302; pve-lab 16 threads, 26.7 GiB available, `local-lvm` empty; token ACLs: no `/nodes/pve-lab` | `ping`, `ip neigh`, `pvesh`, `pveum acl list` on 192.168.0.16 | 2026-11-17 |
| Host-key script | Pinned VM 302 (.32) with the same fingerprint as the manual check (`SHA256:uWRZ…noj8`); refuses 192.168.0.14 | `scripts/pin-guest-hostkey.sh` into a scratch known_hosts | 2026-11-17 |
| Offline checks | PASS | `make k3s-cluster-check`, `scripts/check-quality.py` | 2026-11-17 |
| Plan | 2 to add, 0 change, 0 destroy: image download on pve-lab `local` and VM 310 `k3s-server-01` (pve-lab, 6 vCPU, 12288 MiB, 64 GiB, 192.168.0.40/24); SHA256 `afe3f7c15710283812684103a0664f284f7d624465b1f22f4f9df0e5a610f0b5` | `make k3s-cluster-plan` | 2026-11-17 |

## Completion summary

_Not completed._ Remaining: ACL `/nodes/pve-lab` and `K3S_TOKEN` (blocked by Claude Code's permission
classifier pending the operator's specific OK), then apply, host keys, configure, kubectl, rebuild proof.
