---
title: TASK-017 — Shared NFS storage VM on pve-core and nvme-shared StorageClass
description: storage-01 (VM 350, .50, 300 GiB data disk) exports NFSv4 to the k3s nodes only; csi-driver-nfs 4.13.6 with a Retain class for user data; app data stays on local-path.
published: true
tags:
- task
- completed
- storage
- nfs
- k3s
- opentofu
- ansible
editor: markdown
date: '2026-11-17T00:00:00.000Z'
dateCreated: '2026-11-17T00:00:00.000Z'
---

# TASK-017 — Shared NFS storage VM on pve-core and nvme-shared StorageClass

> **ID:** TASK-017 · **Type:** task · **Status:** completed · **Updated:** 2026-11-17 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-017-shared-nfs-storage-vm-on-pve-core-and-nvme-shared-storagecla.md)

## Goal

M006: user data of k3s applications lives outside the k3s cluster and survives pod and k3s VM replacement.

## Context

- [ADR-012](/docs/decisions/adr-012-external-nvme-storage-truenas-backups); operator direction 2026-11-17, which refines
  it: **app/runtime data may stay on the node, user data (e.g. Forgejo repositories) must live outside the
  cluster**, on a shared volume served from `pve-core` (1 TB NVMe) until an SSD/NVMe on the NAS is dedicated.
  This replaces M006's earlier exclusion of NFS for live volumes: the share comes from a VM, never from a hypervisor.

## Design

- **VM** `terraform/stacks/storage`: `storage-01`, VM 350, pve-core, 192.168.0.50, 2 vCPU / 2 GiB, 16 GiB OS
  disk plus a separate 300 GiB thin data disk (`scsi1`; raise `data_disk_gb`, Ansible grows ext4; max 700).
  `prevent_destroy`; own image copy (the runner root owns the other copy on pve-core).
- **Role** `nfs_server`: ext4 on the data disk (never re-formatted), `/srv/k3s`, NFSv4 only, export and
  nftables limited to the k3s node range 192.168.0.40–49; `no_root_squash` because the CSI driver creates and
  chowns one directory per volume.
- **k3s**: `nfs-common` on the nodes; chart `csi-driver-nfs` 4.13.6 (pinned); StorageClass **`nvme-shared`**
  (not default, `Retain`, `onDelete: retain`, directory `<namespace>/<pvc-name>`). `local-path` stays the
  default class for app/runtime data on the node.
- **Failure domain (no HA claimed):** one VM on one host (`pve-core`) and one NVMe; if it is down, pods using
  `nvme-shared` hang on I/O (hard mounts) until it returns; a lost disk loses the data. No backup yet:
  backups to TrueNAS come with M012; do not put irreplaceable data here before that.

## Acceptance criteria

- [x] Offline: root tests (3), playbook syntax, role/StorageClass/Make guard tests
- [x] A test application keeps its data across pod deletion, k3s VM reboot and k3s VM replacement
- [x] The storage failure domain is documented without HA claims

## Verification

```
make storage-check
infisical run --silent --env dev --path /pve-management -- make storage-plan MGMT_INPUT_SOURCE=env STORAGE_ALLOCATION_REVIEWED=yes
make storage-hostkeys && make storage-configure STORAGE_CONFIGURE_APPROVED=yes
make storage-csi-deploy STORAGE_CSI_DEPLOY_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `terraform/stacks/storage/tests/storage.tftest.hcl` | VM contract (two disks), refusal of .14, other nodes/ranges, oversized disk | `make storage-check` | PASS (3) 2026-11-17 |
| `tests/storage.py` | exports and firewall for k3s nodes only, no re-format, Retain class not default, class points at storage-01, pinned chart, Make guards | `make storage-check` | PASS 2026-11-17 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Plan / apply | 2 to add (own image copy, VM 350 with 16 + 300 GiB disks); applied; plan SHA256 `c0f145ec…f559` | `make storage-plan`, `make storage-apply` | 2026-11-17 |
| Host key | Network and on-disk keys agreed, pinned | `make storage-hostkeys` | 2026-11-17 |
| Configure | First run failed: `/etc/exports.d` missing on Debian 13 (role now creates it); then ok=20 changed=8, second run changed=0 | `make storage-configure` | 2026-11-17 |
| NFS state | `/srv/k3s` 295 GiB ext4 on the data disk; exports only 192.168.0.40/29 and .48/31; the workstation cannot reach port 2049 | `df`, `exportfs -v`, TCP probe | 2026-11-17 |
| CSI | `nvme-shared` (nfs.csi.k8s.io, Retain) beside `local-path (default)` | `kubectl get sc` | 2026-11-17 |
| Persistence | A pod wrote a file through an `nvme-shared` PVC; read back by a new pod after pod deletion, after a k3s VM reboot, and after a full k3s VM **replacement** (new cluster, new PVC with the same namespace/name finds the same directory) | `kubectl`, `make k3s-cluster-*` | 2026-11-17 |
| Operator slip | One rebuild attempt passed a malformed checksum; `k3s-cluster-apply` refused it and nothing changed; rerun with the right SHA256 | Make guard output | 2026-11-17 |

## Completion summary

Completed 2026-11-17. User data goes to `storageClassName: nvme-shared` (on `storage-01`, outside k3s);
everything else may use the default `local-path` on the node. After a single-server cluster rebuild the
platform pieces are redeployed with `make storage-csi-deploy` and `make headlamp-deploy` (Argo CD will do
this from M009), and re-created PVCs find their data by name.
Open: backups of `/srv/k3s` (M012); move to NAS-backed or Ceph storage later (M011); monitoring of free space (monitoring milestone).
