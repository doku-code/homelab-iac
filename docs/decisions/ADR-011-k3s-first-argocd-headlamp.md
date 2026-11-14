---
id: ADR-011
title: "k3s is the application platform from the start, reconciled by Argo CD and administered with Headlamp"
summary: "New applications run on k3s (OpenTofu VMs, Ansible bootstrap, embedded etcd); Argo CD reconciles them from Forgejo; Headlamp is the Kubernetes UI; Windmill automates workflows. Supersedes ADR-006."
type: decision
status: accepted
importance: 5
created: 2026-11-14
updated: 2026-11-14
tags: [decision, kubernetes, k3s, argocd, headlamp, windmill]
component: application
topics: [k3s, argocd, headlamp, windmill, gitops, etcd]
related: [ARCH-platform, ADR-005, ADR-012, ADR-014]
related_tasks: []
related_milestones: [M004, M005, M009]
supersedes: [ADR-006]
superseded_by: []
---

# ADR-011: k3s first, Argo CD for GitOps, Headlamp for administration

## Context

ADR-006 chose Docker Compose first and Kubernetes later. The operator has confirmed k3s as the
application platform from the beginning of the new infrastructure.

## Decision

- **k3s** runs new applications. Its VMs are created with OpenTofu and configured with Ansible. The
  first cluster may be a single server; the datastore direction is **embedded etcd**, configured so
  servers can be added later. The cluster never depends on a database hosted inside itself.
  Initial availability (single node) and the later HA design (more servers spread over Proxmox hosts,
  topology constraints) are documented separately in M004 and M011.
- **Headlamp** (kubernetes-sigs/headlamp, official Helm chart) is deployed right after the bootstrap as
  the graphical administration and troubleshooting UI: nodes, workloads, PVC/PV/StorageClasses, events,
  logs. Kubernetes RBAC-based authentication, reachable only from trusted administration networks;
  `kubectl` keeps working without it.
- **Argo CD** reconciles Kubernetes applications and platform manifests from Forgejo once operational.
- **Windmill** runs operational workflows and schedules and may trigger Forgejo workflows; it does not
  duplicate OpenTofu, Ansible or Argo CD ([ADR-005](ADR-005-windmill-service-catalog.md)).
- The **dedicated Forgejo runner** executes approved deployment jobs ([ADR-014](ADR-014-dedicated-forgejo-deployment-runner.md)).
- Docker Compose remains for bootstrap services and documented compatibility exceptions only.
  Flux (legacy Stage A) is not the target.

## Consequences

- Responsibilities: Headlamp inspects and administers, Argo CD reconciles from Git, Windmill automates
  workflows, the runner executes approved jobs.
- Persistent application data does not live on k3s VM disks (ADR-012).
