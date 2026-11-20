---
title: 'ADR-012: External NVMe-backed Kubernetes storage, TrueNAS for backups, Ceph later'
description: PVCs come through CSI from NVMe-backed storage outside k3s on the physical hosts; TrueNAS only receives backups; Ceph (RBD, CephFS) is the future distributed layer.
published: true
tags:
- decision
- accepted
- storage
- nvme
- csi
- truenas
- ceph
- backup
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# ADR-012: External NVMe-backed Kubernetes storage, TrueNAS for backups, Ceph later

> **ID:** ADR-012 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-012-external-nvme-storage-truenas-backups.md)

## Context

An earlier proposal used TrueNAS (NFS/iSCSI CSI) as the live Kubernetes storage. The operator rejected
it (2026-11-14): live application data must use the NVMe drives of the physical Proxmox hosts, and
TrueNAS must hold backups. No accepted ADR selected TrueNAS CSI; this record closes the question.

## Decision

- **Principle:** application persistent data lives on a storage service architecturally separate from
  the k3s cluster and consumed through a CSI driver, StorageClasses and PVCs. Rebuilding a k3s VM must
  not destroy application data. This says nothing about tolerating host or storage-server failures:
  failure domains are documented per implementation.
- **Hardware:** the local NVMe drives of the physical hosts. Local disks alone give no shared storage,
  provisioning or replication, so an explicit storage layer is deployed.
- **Initial layer (M006):** the simplest viable NVMe-backed service external to k3s for the hardware
  actually available (for example a dedicated storage VM, or a Proxmox-integrated technology), with a
  supported CSI driver. A single-host service is acceptable during the rebuild if its limits are
  documented; it is never labelled highly available. No ad-hoc NFS exports on hypervisors.
- **Future layer (M011):** **Ceph**, independent of the k3s application cluster, OSDs on the hosts'
  NVMe drives once enough hosts, disks and network bandwidth exist: **RBD** for databases and
  single-writer volumes, **CephFS** for ReadWriteMany. Not forced onto too few nodes.
- **StorageClasses** follow the real backend and driver; candidate names `nvme-block`, `nvme-shared`,
  later `ceph-rbd`, `cephfs` (not deployed). RWO for single writers, RWX only on a real shared
  filesystem. Critical volumes use `reclaimPolicy: Retain`. Changing backends means copying data.
- **TrueNAS SCALE** is the backup and recovery destination (storage, VM, database and application
  backups). It provides no live PVCs: no TrueNAS CSI, NFS or iSCSI for new applications, and no active
  PostgreSQL data. Current services on TrueNAS (Forgejo) stay until their replacement is ready.

## Consequences

- Ceph replicates blocks; Patroni replicates PostgreSQL (ADR-013); neither replaces application-aware
  backups to TrueNAS (M012). No automatic ZFS-to-Ceph synchronisation is assumed.
- The storage implementation, protocol and CSI driver are pending until the NVMe inventory (M002/M006).
