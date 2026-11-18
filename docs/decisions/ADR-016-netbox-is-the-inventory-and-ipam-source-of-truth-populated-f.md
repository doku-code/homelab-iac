---
id: ADR-016
title: NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery
summary: NetBox on k3s holds the intended inventory and address plan; Git owns what OpenTofu defines, Proxmox is only observed, NetBox is never a bootstrap dependency.
type: decision
status: accepted
importance: 4
created: 2026-11-18
updated: 2026-11-18
tags: [decision, netbox, inventory, ipam]
component: inventory
topics: [netbox, inventory, ipam, source-of-truth, ansible-inventory, proxmox-discovery]
related: [ARCH-platform, ADR-011, ADR-012, ADR-015, ADR-004, ADR-005]
related_tasks: [TASK-023]
related_milestones: [M013]
supersedes: []
superseded_by: []
---

# ADR-016: NetBox is the inventory and IPAM source of truth, populated from Git and read-only discovery

## Context

Host facts were spread over the variable files of six OpenTofu roots, the validations that encode the
address plan, a DNS variable file, the legacy Proxmox host and the operator's memory. Nothing listed every
machine, its host, its address and whether anyone had verified it; the OpenTofu state that does hold the
new VMs lives on the workstation only, so the deployment runner, Windmill and CI cannot read it. The
operator asked (2026-11-18) for NetBox as the inventory and IPAM platform, integrated into the existing
rebuild rather than added beside it.

## Decision

**Where it runs.** NetBox Community 4.7 on k3s, official chart `netbox-community/netbox` (pinned), one web
pod and one worker pod. Database on the shared PostgreSQL outside k3s (ADR-015); uploaded media on the
`nvme-shared` volume (ADR-012); a single pinned official Valkey in the cluster as queue and cache, without
persistence. The chart's bundled PostgreSQL and Valkey sub-charts are disabled: the Valkey one pulls an
unpinned image and defaults to replication. No plugins, one custom field (`proxmox_vmid`). Reachable from
the LAN only, login required, at `https://netbox.doku-lab.net`.

**What it is not.** NetBox is not needed to build or rebuild anything below it or beside it. Every OpenTofu
root keeps its own variables and writes its own Ansible inventory; DNS, PostgreSQL, k3s and Phase are
deployed without it. When NetBox is down, provisioning and configuration work as before and only the
reconciliation and the NetBox-backed inventory wait. NetBox holds no credentials.

**Who owns which data.**

| Data | Authority | NetBox's part |
|------|-----------|---------------|
| VMs of the OpenTofu roots: name, VMID, Proxmox host, address, role, platform | Git (root variables, read through `tofu output`) | Mirror, tag `iac`; the reconciliation overwrites these fields |
| Sizing of those VMs (vCPU, memory, boot disk) | Proxmox API (observed) | Informational copy |
| Address plan: prefix, ranges per role | Git today (`services/netbox/inventory.yaml`, same numbers as the root validations) | Mirror; becomes the authority when a root reads its addresses from NetBox (see below) |
| Physical devices, their hardware, location, cabling; unmanaged equipment | NetBox | Seeded once from `inventory.yaml`, then edited only in NetBox |
| Guests no root defines (the legacy host) | NetBox, after a person validated them | Created once from discovery with tags `discovered` and `needs-review`; later differences are reported, never written |
| Runtime state (running, stopped, where) | Proxmox and Kubernetes APIs | Compared and reported |
| Kubernetes workloads | Argo CD / Git | Not inventoried; the k3s node VMs are |
| OS and host configuration | Ansible / Git | Not stored |
| Credentials | Phase | Never stored |
| Decisions and procedures | this repository and its wiki | Not stored |

One writer per field: the reconciliation (`scripts/netbox-sync.py`, account `inventory-sync`: view, add,
change, no delete) writes the `iac` fields and creates seed and discovered records once; people write
everything else in the web interface. Nothing writes from NetBox back to Git or to Proxmox, so there is no
loop. Deleting a record is always a person's decision.

**How it is kept current.** `make netbox-discover` takes a read-only snapshot of a Proxmox environment
(GET requests only); `make netbox-plan` prints what would change and what needs a decision; `make
netbox-apply` writes. A snapshot older than 24 hours can be planned from but not applied.

**First consumer.** Ansible reads the `iac` VMs through `netbox.netbox.nb_inventory`
(`ansible/inventories/netbox.yml`, account `automation-read`: view only), with the group names the
playbooks already use. It serves runs across roots and consumers without the OpenTofu state; it does not
replace the per-root inventories that bootstrap the platform.

## Alternatives considered

- **NetBox on its own VM (Docker Compose).** Independent of k3s, but one more machine to patch and back up,
  and NetBox is not a bootstrap dependency, so the independence buys nothing. Rejected; ADR-011 puts
  applications on k3s.
- **The chart's bundled PostgreSQL and Valkey.** A second database to operate and an unpinned image.
  Rejected for the shared PostgreSQL and a pinned Valkey.
- **A NetBox Proxmox plugin (netbox-proxbox, proxmox2netbox).** They need a custom NetBox image, a second
  backend service holding Proxmox credentials, and declare NetBox 4.7 support experimental or unverified.
  They also write observed state straight into the inventory. Rejected for a small script that separates
  intended from observed.
- **Writing NetBox from OpenTofu (`e-breuninger/netbox` provider) in every root.** Every plan would need
  NetBox, which makes it a bootstrap dependency of the platform that hosts it. Rejected for now; see below.
- **NetBox allocating addresses during provisioning.** An allocation at plan time is a write that a failed
  or abandoned plan leaves behind, and two plans can race. Deferred: addresses stay chosen in Git, where a
  commit is the reservation.

## Consequences

- One place lists every machine with its host, address, role and whether it was verified.
- Two copies of the VM identity exist (Git and NetBox); the reconciliation keeps them equal and the plan
  shows any difference. A change made to an `iac` field in NetBox is overwritten at the next apply.
- The NetBox database is on the shared PostgreSQL and is covered by whatever backs that up (M012); media
  is on `storage-01`. Losing the NetBox secrets in Phase costs the sessions and API tokens, not the data:
  run `make netbox-identities` again.
- Next steps, in order of value: (1) a check in each root's plan target that its addresses and VMIDs are
  free in NetBox, replacing the manual `*_ALLOCATION_REVIEWED` reading; (2) NetBox as the place where the
  next free address of a range is looked up before it is written to Git; (3) Windmill forms that read roles
  and ranges from NetBox with the read-only account; (4) Prometheus targets from NetBox. Each must keep
  working, with a clear message, when NetBox is unreachable.
