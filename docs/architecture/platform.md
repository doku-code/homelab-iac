---
id: ARCH-platform
title: Target homelab platform architecture
summary: "Layers and owners of the rebuilt homelab: Proxmox cluster, k3s, Headlamp, external NVMe storage via CSI, PostgreSQL/Patroni, Phase, Argo CD, Windmill, runner; TrueNAS for backups."
type: architecture
status: current
importance: 5
created: 2026-11-12
updated: 2026-11-14
tags: [architecture, platform, rebuild]
component: platform
topics: [proxmox, cluster, k3s, headlamp, argocd, windmill, storage, nvme, csi, ceph, truenas, postgresql, patroni, phase, forgejo, runner, opentofu, ansible]
applies_to: [terraform, ansible, kubernetes]
related: [DOC-project-overview, INV-legacy-inventory, GUIDE-handoff]
related_decisions: [ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014]
related_implementations: []
---

# Target homelab platform architecture

## Overview

The homelab is rebuilt as a reproducible platform declared in this repository. The rebuild is
**rolling** ([ADR-001](../decisions/ADR-001-rolling-infrastructure-rebuild.md)): the existing
infrastructure builds its replacement, services move one at a time, and reclaimed hardware is
reinstalled and joins the new cluster.

**Proxmox → k3s → Headlamp → external NVMe-backed storage / CSI → PostgreSQL + Patroni → Phase →
Argo CD + Windmill → applications.**

This document is the target. Deployed state is in milestone and task evidence; the legacy estate is
in [INV-legacy-inventory](../investigations/legacy-inventory.md); the current step is in the
[handoff](../handoff.md).

## Structure

```mermaid
flowchart TB
  subgraph phys["Physical Proxmox infrastructure (new cluster, ADR-010)"]
    pm["pve-management<br/>local NVMe"]
    pc["pve-core<br/>local NVMe"]
    px["reclaimed hosts<br/>local NVMe"]
  end
  subgraph store["External storage layer (ADR-012)"]
    s1["initial NVMe-backed service<br/>outside k3s"]
    ceph["future Ceph RBD / CephFS"]
  end
  subgraph k8s["k3s compute (ADR-011)"]
    csi["CSI drivers → StorageClasses → PVCs"]
    pg["PostgreSQL + Patroni (ADR-013)"]
    apps["Phase, Windmill, Authentik, applications"]
    argo["Argo CD"]
    hl["Headlamp"]
  end
  ws["mgmt-control-01<br/>Ubuntu Desktop workstation"]
  fj["Forgejo + dedicated runner (ADR-014)"]
  nas["TrueNAS SCALE<br/>backup destination only"]
  pm --- s1
  pc --- s1
  px -.-> ceph
  s1 --> csi
  ceph -.-> csi
  csi --> pg
  csi --> apps
  pg --> apps
  fj --> argo
  argo --> apps
  ws --> fj
  ws --> hl
  s1 -. backups .-> nas
  pg -. database backups .-> nas
  apps -. application backups .-> nas
```

### Layers and owners

Each layer has one owner; a tool never writes objects another layer owns.

| # | Layer | Technology | Owns | Never does |
|---|-------|------------|------|------------|
| 1 | Physical infrastructure | Proxmox VE cluster on `pve-management`, `pve-core`, reclaimed hosts ([ADR-010](../decisions/ADR-010-new-proxmox-cluster-on-pve-management.md)) | Compute, local NVMe, bridges | Application stacks or ad-hoc NFS exports on hypervisors |
| — | Provisioning / OS config | OpenTofu `bpg/proxmox` ([ADR-003](../decisions/ADR-003-opentofu-for-new-infrastructure.md)) / Ansible | VMs, disks, NICs / packages, users, k3s install | App topology |
| 2 | Kubernetes compute | k3s, embedded etcd ([ADR-011](../decisions/ADR-011-k3s-first-argocd-headlamp.md)) | Workload scheduling | Hold persistent data on its VM disks |
| 3 | Persistent storage | NVMe-backed service external to k3s; Ceph later ([ADR-012](../decisions/ADR-012-external-nvme-storage-truenas-backups.md)) | Volumes, their failure domain | Depend on the k3s cluster it serves |
| 4 | CSI integration | CSI driver of the chosen backend; StorageClasses (`nvme-block`, `nvme-shared`, later `ceph-rbd`, `cephfs`) | Dynamic PVC provisioning | Exist for a backend that does not support it |
| 5 | Central database | PostgreSQL + Patroni, Zalando operator pending validation ([ADR-013](../decisions/ADR-013-central-postgresql-patroni.md)) | Per-application databases, roles, replication | Bootstrap k3s, store data on TrueNAS |
| 6 | Applications | Phase ([ADR-004](../decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)), Windmill, Authentik, migrated services; Compose only for bootstrap exceptions | Their configuration | — |
| 7 | Management tools | Headlamp (UI), Argo CD (GitOps), Windmill (workflows, [ADR-005](../decisions/ADR-005-windmill-service-catalog.md)), Forgejo + dedicated runner ([ADR-014](../decisions/ADR-014-dedicated-forgejo-deployment-runner.md)), workstation `mgmt-control-01` ([ADR-009](../decisions/ADR-009-management-vm-gnome-admin-workstation.md)) | Inspect / reconcile / automate / execute | Duplicate each other or OpenTofu/Ansible |
| 8 | Backup storage | TrueNAS SCALE (and PBS for guests) | Storage, VM, database and application backups | Provide live PVCs (no TrueNAS CSI/NFS/iSCSI for applications) |
| — | Edge, identity, observability | Caddy and/or ingress, AdGuard Home, pfSense; Authentik; Prometheus, Loki, Grafana | HTTPS, DNS, routing; SSO; metrics, logs, alerts | Sit in the bootstrap path |

Secrets: Infisical stays in use until secrets migrate incrementally to Phase (M008); SOPS + age for
bootstrap material is deferred to M012.

### Hosts

| Host | Now | Target |
|------|-----|--------|
| `pve-management` 192.168.0.10 | Operational, standalone; runs `mgmt-control-01` (VM 100) | Founding node of the new cluster |
| `pve-core` | Emptied, workloads moved to `pve-lab` | Reinstalled, first node joined (M002, TASK-013) |
| `pve-lab` | Hosts legacy and former `pve-core` workloads | Continuity host; reclaimed after migration (M010) |
| `pve-k8s-01/02` | Legacy | Reclaimed after migration |
| TrueNAS SCALE | Serves Forgejo and datasets | Backup destination; current apps stay until replaced |
| `pve-infra`, `pve-compute` | **Retired**, no longer exist | — |

Two nodes have no quorum tolerance (QDevice evaluated in M002); a cluster creates no shared storage;
initial availability and later HA are designed separately (M004, M011).

### Repository layout

Infrastructure code keeps the `terraform/` tree: new roots are OpenTofu roots under
`terraform/stacks/<host>-<purpose>/` reusing `terraform/modules/*`; legacy roots stay on Terraform
until migrated ([ADR-007](../decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)).
Ansible roles under `ansible/roles/`, workflows under `.forgejo/workflows/`, Kubernetes manifests and
Helm values reconciled by Argo CD in a directory chosen in M004/M009.

### State

OpenTofu state is local on the operator workstation (`mgmt-control-01`), one writer at a time, never
in Git. A shared backend is decided only when the dedicated runner must apply (TASK-010, M003).

## Key flows

- **New service:** define the deployment (manifests or Helm values) → Argo CD reconciles it on k3s →
  PVCs from the external NVMe-backed StorageClass → database and role on the central PostgreSQL →
  secrets from Phase (Infisical until then) → ingress/DNS → health check. Windmill may trigger the
  workflow; every step stays runnable from the workstation.
- **Migrate a service (M010):** deploy the replacement, copy its data, configure database and secrets,
  validate, cut over, retire the old workload only after validation.
- **Reclaim a host:** confirm it is empty → guard legacy roots → reinstall Proxmox → join the cluster
  → add k3s and storage capacity.

## Constraints

- No apply/destroy, reinstall, cluster, storage, network, firewall or credential change without
  explicit operator approval of that operation.
- Never destroy an original workload or its data before the replacement works.
- Single-host storage is never labelled HA; no Ceph on too few nodes.
- Validation CI receives no infrastructure credentials; CT301 stays validation-only.
- Verify licences and self-hosting support (Phase, operators, charts) when their milestone starts.
