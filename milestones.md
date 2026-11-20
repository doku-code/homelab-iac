---
title: Milestones
description: 'Milestones: index of milestones/ in the homelab-iac repository'
published: true
tags:
- index
editor: markdown
---

# Milestones

> Generated from the repository: [milestones/](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/milestones/)

## Documents

| Document | Status | Summary |
|----------|--------|---------|
| [M000 — Infrastructure inventory and migration planning](/milestones/m000-inventory-and-migration-planning) | active | Accurate live inventory of hosts, guests, services, data and backups, and a migration order that avoids unnecessary downtime. |
| [M001 — Management workstation](/milestones/m001-bootstrap-pve-management) | completed | Existing infrastructure provisions and configures the management workstation VM on pve-management from IaC, and operations move to it. |
| [M002 — New Proxmox cluster (four nodes)](/milestones/m002-proxmox-compute-capacity) | completed | The new cluster doku-lab runs on pve-management, pve-core, pve-infra and the new pve-lab (.16), quorate, with its hardware and capacity inventoried. |
| [M003 — Dedicated Forgejo deployment runner](/milestones/m003-deployment-runner) | completed | A dedicated runner VM, built with OpenTofu and Ansible, executes approved infrastructure workflows from the existing Forgejo with scoped credentials. |
| [M004 — k3s bootstrap](/milestones/m004-k3s-bootstrap) | completed | The first k3s cluster (one or more VMs, embedded etcd) is provisioned with OpenTofu, configured with Ansible and reachable with kubectl. |
| [M005 — Headlamp](/milestones/m005-headlamp) | completed | Headlamp is deployed with its official Helm chart, RBAC-based authentication and network restriction, and shows nodes, workloads, storage objects, events and logs. |
| [M006 — External NVMe-backed storage](/milestones/m006-external-nvme-storage) | completed | Kubernetes provisions PVCs through CSI from an NVMe-backed storage service outside k3s; data survives pod and k3s VM replacement; the failure domain is documented. |
| [M007 — PostgreSQL platform](/milestones/m007-postgresql-platform) | completed | PostgreSQL 17 runs on three Patroni VMs outside k3s (one per Proxmox host) with automatic failover and a virtual IP; per-application databases and roles. |
| [M008 — Phase](/milestones/m008-phase) | completed | Phase runs on k3s with its supported database and storage, issues service identities, and new deployments read their secrets from it. |
| [M009 — Argo CD and Windmill](/milestones/m009-argocd-windmill) | active | Argo CD reconciles Kubernetes applications from Forgejo and Windmill runs operational workflows integrated with the repository and the runner. |
| [M010 — Rolling application migration](/milestones/m010-rolling-application-migration) | planned | Applications move one at a time to k3s with their data, secrets and databases, are validated, cut over, and the old workloads retired; freed hosts join the cluster. |
| [M011 — Ceph and infrastructure expansion](/milestones/m011-ceph-and-expansion) | planned | With enough hosts and NVMe devices, Ceph (RBD, CephFS) provides distributed storage through CSI, selected PVCs migrate to it and PostgreSQL replicas spread across hosts. |
| [M012 — Backups and finalization](/milestones/m012-backups-and-finalization) | planned | Persistent data is inventoried and backed up to TrueNAS with tested, database-aware restores, and the obsolete infrastructure is retired. |
| [M013 — NetBox inventory and IPAM](/milestones/m013-netbox-inventory-and-ipam) | active | NetBox runs on k3s as the inventory and IPAM source of truth, is populated from OpenTofu outputs and read-only Proxmox discovery, and Ansible can read its inventory from it. |
| [M014 — Single sign-on with Authentik](/milestones/m014-single-sign-on-with-authentik) | active | Authentik runs on k3s and signs the operator in to the web interfaces of the platform; each new service is added to it in the same change, and every service keeps a local administrator. |
