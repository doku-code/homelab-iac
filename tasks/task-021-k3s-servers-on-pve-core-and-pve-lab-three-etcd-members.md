---
title: 'TASK-021 — k3s servers on pve-core and pve-lab: three etcd members'
description: k3s-server-02 on pve-core and k3s-server-03 on pve-lab join the embedded etcd; Traefik runs on every node so ingress survives a reschedule.
published: true
tags:
- task
- completed
- k3s
- etcd
- traefik
- proxmox
editor: markdown
date: '2026-11-18T00:00:00.000Z'
dateCreated: '2026-11-18T00:00:00.000Z'
---

# TASK-021 — k3s servers on pve-core and pve-lab: three etcd members

> **ID:** TASK-021 · **Type:** task · **Status:** completed · **Updated:** 2026-11-18 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-021-k3s-servers-on-pve-core-and-pve-lab-three-etcd-members.md)

## Goal

Operator direction 2026-11-18: a second k3s node on `pve-core` and a third on `pve-lab` ("yes it will run 2
nodes for now").

## Context

- [TASK-015](/tasks/task-015-k3s-cluster-on-doku-lab-first-server-on-pve-lab) built `k3s-server-01` with embedded
  etcd (`cluster-init`); more servers are entries in the private `terraform/stacks/k3s/terraform.tfvars`.
- Addresses `192.168.0.40-49` are already allowed as clients of the NFS export, of PostgreSQL and of the
  ingestion routes, so no access rule changed.

## Design

- **Allocation:** `k3s-server-02` VM 311, `192.168.0.41`, `pve-core`, 4 vCPU / 8 GiB / 64 GiB;
  `k3s-server-03` VM 312, `192.168.0.42`, `pve-lab`, 4 vCPU / 6 GiB / 64 GiB (pve-lab has 28 GiB with 16 GiB
  already allocated). All three are servers: three etcd members.
- **Placement limit (accepted by the operator):** two of the three members are on `pve-lab`. Losing
  `pve-core` is tolerated; losing `pve-lab` stops the Kubernetes API until it is back. A third host for the
  third member removes this limit.
- **Image file:** on `pve-core` the bare image name already belongs to the `deploy-runner` root, so this
  root's copy there is prefixed `k3s-`; `pve-lab` keeps the name the running first server was created from.
- **Ingress:** the Traefik Service keeps `externalTrafficPolicy: Local` (client addresses for the
  allow-lists), which makes a node answer only when Traefik runs on it. Traefik is now a DaemonSet, so
  `*.192.168.0.40.sslip.io` keeps working wherever pods move, and every node address serves ingress.
- Volumes of the default `local-path` class stay on the node that created them (Prometheus, Loki, Redis are
  on `k3s-server-01`); user data is on `nvme-shared` and follows the pod.

## Acceptance criteria

- [x] Plan adds only the two VMs and one image; the running server is not touched
- [x] Three nodes Ready, three etcd voters
- [x] Ingress answers on every node; existing services still answer
- [x] The API keeps accepting writes with one server stopped
- [x] Monitoring agents on the new nodes; metrics from all three nodes

## Verification

```
make k3s-cluster-check
scripts/secrets.py run /pve-management -- make k3s-cluster-plan K3S_CLUSTER_ALLOCATION_REVIEWED=yes MGMT_INPUT_SOURCE=env
scripts/secrets.py run /k3s -- make k3s-cluster-configure K3S_CLUSTER_CONFIGURE_APPROVED=yes
make observability-agents OBSERVABILITY_AGENTS_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `terraform/stacks/k3s/tests/k3s.tftest.hcl` | one image per hosting node; `pve-lab` keeps the bare image name, other nodes get the prefixed copy | `make k3s-cluster-check` | PASS 2026-11-18 (5 runs) |
| `tests/k3s-cluster.py` | Traefik values: `Local` policy and DaemonSet; join configuration of later servers | `make k3s-cluster-check` | PASS 2026-11-18 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| First plan | Would have created a second file with the name owned by `deploy-runner` on `pve-core`; caught before apply, image name prefixed | `local:import` listing of pve-core | 2026-11-18 |
| Plan | 3 to add, 0 to change, 0 to destroy (image on pve-core, VM 311, VM 312) | `.local/k3s-plan-servers-02-03.txt` | 2026-11-18 |
| Apply | 3 added; host keys of .41 and .42 pinned | `.local/k3s-apply-servers-02-03.log`, `make k3s-cluster-hostkeys` | 2026-11-18 |
| Configure | `k3s-server-01` changed=1 (Traefik values), `-02` and `-03` changed=16, failed=0 | `.local/k3s-configure-servers-02-03.log` | 2026-11-18 |
| Cluster | 3 nodes Ready `control-plane,etcd` v1.35.8+k3s1; `EtcdIsVoter` True on all three; `/readyz` ok | `kubectl get nodes`, node conditions | 2026-11-18 |
| Ingress | Traefik DaemonSet 3/3; Phase health 200 through .40, .41 and .42; Phase, Grafana, Headlamp answer on their names | `curl --resolve` | 2026-11-18 |
| One server stopped | k3s stopped on `k3s-server-02` for 44 s: `/readyz` ok 20 of 20, a ConfigMap write accepted, Phase 200; node Ready again after the start | `systemctl stop k3s`, `kubectl` | 2026-11-18 |
| Monitoring | Agents installed on both nodes (changed=9, failed=0); 8 hosts report; container and node-state metrics for 3 nodes; 2,790 series in total; no alert firing | `make observability-agents`, PromQL | 2026-11-18 |

## Completion summary

Completed 2026-11-18. Not verified: a real loss of a Proxmox host (the test stopped the k3s service of one
server, not the VM), and a stop of `pve-lab`, which is expected to stop the API (two of three members).
The admin kubeconfig and the published names still point at `192.168.0.40`: when `k3s-server-01` is down the
cluster keeps running, but `kubectl` and the `*.192.168.0.40.sslip.io` names need another node's address
until a shared address exists.
