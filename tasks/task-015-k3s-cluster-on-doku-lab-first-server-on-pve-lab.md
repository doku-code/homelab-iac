---
title: 'TASK-015 — k3s cluster on doku-lab: first server on pve-lab'
description: terraform/stacks/k3s VMs (for_each, rebuildable), k3s role with embedded etcd, token in Infisical /k3s, host keys pinned out-of-band, workstation kubeconfig (ADR-011).
published: true
tags:
- task
- completed
- k3s
- opentofu
- ansible
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-17T00:00:00.000Z'
---

# TASK-015 — k3s cluster on doku-lab: first server on pve-lab

> **ID:** TASK-015 · **Type:** task · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab.md)

**Authorization:** operator granted standing autonomy for goal-directed work on 2026-11-17; Claude Code still
asks the operator for credential and privilege changes (ACL, Infisical secret).

## Goal

M004: the first k3s cluster (embedded etcd, ready for more servers) is provisioned with OpenTofu, configured
with Ansible and reachable with kubectl from the workstation; a node can be rebuilt from IaC.

## Context

- [ADR-011](/docs/decisions/adr-011-k3s-first-argocd-headlamp) (k3s, embedded etcd), [ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups) (no data on VM disks)
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
- [x] `tofu@pve!mgmt` may place VMs on pve-lab (ACL `/nodes/pve-lab`) and `K3S_TOKEN` exists in Infisical
- [x] Plan (image + VM 310 only) applied; host key pinned out-of-band; configure converges, second run changed=0
- [x] `kubectl get nodes` from the workstation: `k3s-server-01` Ready (control-plane, etcd)
- [x] Rebuild from IaC: replace VM 310, re-pin, configure → node Ready again

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
| ACL + token (operator-authorized rule) | `IaCManagementVM` on `/nodes/pve-lab` for `tofu@pve` and `!mgmt`; `K3S_TOKEN` (64 hex) generated locally into Infisical `dev:/k3s`, local copy shredded | `pveum acl list` on .16, `infisical run` (length only) | 2026-11-17 |
| Apply | 2 added (image 12 s, VM 310 2 min 8 s); only the expected guest-agent warning, now after 2 min | `make k3s-cluster-apply` | 2026-11-17 |
| Host key | Network and on-disk keys agreed: `SHA256:/Ce1uzvwMy+1Yc7GMgsO9gWOShq7AxtA8t99UuS4ZCA` pinned | `make k3s-cluster-hostkeys` | 2026-11-17 |
| Configure | Run 1: ok=25 changed=16; run 2: ok=23 changed=0 | `make k3s-cluster-configure` | 2026-11-17 |
| Kubeconfig bug | kubectl prompted for a username: the context rename missed the `- name: default` list items; fixed regex, regression test renders the playbook's transform (fails on the old regex) | `tests/k3s-cluster.py` | 2026-11-17 |
| kubectl from the workstation | `k3s-server-01 Ready control-plane,etcd v1.35.8+k3s1 192.168.0.40`; coredns, local-path, metrics-server, traefik, svclb Running | `kubectl get nodes -o wide`, `kubectl get pods -A` | 2026-11-17 |
| Rebuild from IaC | Plan `K3S_CLUSTER_REPLACE=k3s-server-01`: 1 add, 1 destroy (SHA256 `861a097c…762b`); apply (destroy 3 s, create 2 min 10 s), new key `SHA256:iOdsSABdS6U7IBrqfkVNoeg4HvDVMAUidzOP/r+9bnA` pinned out-of-band, configure ok=25 changed=15, node Ready again, `/readyz` and `/readyz/etcd` ok; 191 s end to end; afterwards plan: No changes | `make k3s-cluster-*`, kubectl | 2026-11-17 |
| Verification set | whitespace, fmt, validate, ansible-syntax, offline tests, mgmt/deploy-runner/k3s-cluster checks, quality: PASS | recorded commands | 2026-11-17 |

## Completion summary

Completed 2026-11-17. `k3s-server-01` (VM 310, pve-lab, 192.168.0.40, 6 vCPU / 12 GiB / 64 GiB) runs k3s
v1.35.8+k3s1 with embedded etcd (cluster-init), Traefik and ServiceLB; `kubectl` works from the workstation
(context `doku-lab`). The node was rebuilt from IaC in about 3 minutes (replace, out-of-band host-key pin,
configure) and the cluster came back Ready; OpenTofu reports no drift.

Initial availability: one server, one etcd member, no HA (a lost VM means a fresh cluster until more
servers join; workloads are not yet hosted). Next servers: tfvars entries (pve-core first).
Open, outside this task: local-path-provisioner is k3s's default StorageClass and would put PV data on the
VM disk, against ADR-012: M006 decides (disable or scratch only); etcd snapshots stay on the VM disk until the
backup design (M012); the runner's kubeconfig with scoped RBAC comes with the first runner-deployed workload.
