---
id: GUIDE-map-ci-cd
title: "CI/CD map"
summary: "The Forgejo workflows, what starts them, which runner executes them and the checks they run."
type: guide
status: current
importance: 4
created: 2026-11-25
updated: 2026-11-25
tags: [map, ci, forgejo]
nav_order: 8
related: [ARCH-platform]
related_decisions: [ADR-008, ADR-014]
source_paths: [scripts/docs-maps.py]
---

# CI/CD map

Two runners, separated by trust: `ci-runner-01` (label `homelab-iac`) validates and holds no infrastructure
credential; `deploy-runner-01` (label `homelab-deploy`) runs the gated deployments. No workflow on these runners is
started by a pull request.

## Workflows

<!-- map:workflows:start -->
| Workflow | Runs on | Runner | Repository variables that gate it | Jobs |
|---|---|---|---|---|
| [Deploy](../../.forgejo/workflows/deploy.yml) | workflow_dispatch | `homelab-deploy` | `DEPLOY_RUNNER_APPROVED` | deploy |
| [Documentation validation](../../.forgejo/workflows/harness-docs-validate.yml) | push to main, workflow_dispatch | `homelab-iac` | `CI_QUALITY_APPROVED` | check |
| [Wiki publication](../../.forgejo/workflows/harness-wiki-publish.yml) | push to main, workflow_dispatch | `homelab-iac` | `CI_QUALITY_APPROVED` | publish |
| [Publish CI base image](../../.forgejo/workflows/publish-ci-base.yml) | workflow_dispatch | `homelab-iac` |  | publish |
| [Validate](../../.forgejo/workflows/validate.yml) | push to main, workflow_dispatch | `homelab-iac` | `CI_QUALITY_APPROVED` | validate |
<!-- map:workflows:end -->

## Checks

The verification commands of [`harness.yaml`](../../harness.yaml): all offline, runnable on the workstation and in CI.

<!-- map:checks:start -->
| Check | What it proves |
|---|---|
| `whitespace` | No whitespace errors in the working tree (also enforced in CI) |
| `harness-check` | Frontmatter, links, indexes and sensitive-data rules for docs/, milestones/, tasks/ |
| `quality` | Parses every tracked YAML/Python/shell file and guards the CI activation gate |
| `terraform-fmt` |  |
| `terraform-validate` | Every root with the backend disabled and a throwaway TF_DATA_DIR (never touches local state) |
| `mgmt-check` | OpenTofu root for mgmt-control-01 (fmt, validate, mocked tofu test) plus auth/Make guard tests; offline |
| `deploy-runner-check` | OpenTofu roots deploy-runner and ci-disposable (fmt, validate, mocked tofu test), playbook syntax, wrapper/role/workflow/Make guard tests; offline |
| `k3s-cluster-check` | OpenTofu root k3s (fmt, validate, mocked tofu test), configure-k3s syntax, host-key script, role/template/kubeconfig/Make guard tests; offline |
| `storage-check` | OpenTofu root storage (fmt, validate, mocked tofu test), playbook syntax, NFS role/StorageClass/Make guard tests; offline |
| `postgresql-check` | OpenTofu root postgresql (fmt, validate, mocked tofu test), playbook syntax, Patroni role/access/Make guard tests; offline |
| `ci-runner-check` | OpenTofu root ci-runner (fmt, validate, mocked tofu test), playbook syntax, runner configuration and Make guard tests; offline |
| `dns-check` | OpenTofu root dns (fmt, validate, mocked tofu test), playbook syntax, AdGuard Home role/configuration/Make guard tests; offline |
| `truenas-check` | The NAS's apps as files, placeholders for secrets, gated apply; offline |
| `media-check` | OpenTofu root media (fmt, validate, mocked tofu test), playbook syntax, Compose project, NAS protection, firewall, routes and Make guard tests; offline |
| `phase-check` | Renders the pinned Phase chart and tests scripts/secrets.py with fake stores (workstation only; needs helm, the chart download and age) |
| `observability-check` | Renders the four pinned observability charts, checks allow-lists against dashboard and alert queries, routes and agent templates (workstation only; needs helm and the chart downloads) |
| `ingress-check` | Renders the pinned cert-manager chart and checks issuer, wildcard certificate, Traefik store and the routes carried over from the legacy Caddy (workstation only; needs helm and the chart download) |
| `argocd-check` | Renders the pinned Argo CD chart and checks route, project limits and every Application (workstation only; needs helm and the chart download) |
| `windmill-k3s-check` | Renders the pinned Windmill chart and checks route, database roles and the scripts of windmill/ (workstation only; needs helm and the chart download) |
| `homepage-k3s-check` | Renders the dashboard's manifests and checks route, sign-in, cards and the widget data API on canned data (workstation only; needs kubectl) |
| `wiki-check` | Renders the pinned Wiki.js chart and checks route, database, the documentation export and the configuration tool against an in-memory wiki (workstation only; needs helm and the chart download) |
| `authentik-check` | Renders the pinned Authentik chart and checks route, blueprints and the single sign-on wiring of every application (workstation only; needs helm and the chart download) |
| `netbox-check` | Renders the pinned NetBox chart and runs the inventory reconciliation against an in-memory NetBox (workstation only; needs helm and the chart download) |
| `headlamp-check` | Renders the pinned Headlamp chart and checks access rules (workstation only; needs helm and the chart download) |
| `ansible-syntax` |  |
| `compose-config` | Static Compose validation with synthetic inputs; starts nothing |
| `offline-tests` | Offline test scripts run by CI (mocked providers, synthetic fixtures; flux/homepage need kubectl) |
<!-- map:checks:end -->

## Documentation and wikis

A push to `main` that touches the documentation publishes it twice, from the same commit:

- the Forgejo wiki of the repository ([`scripts/forgejo-wiki.py`](../../scripts/forgejo-wiki.py)): the maps in the
  sidebar, one page per document;
- the page tree that Wiki.js pulls ([`scripts/wiki-export.py`](../../scripts/wiki-export.py), <https://wiki.doku-lab.net>).

Both are generated: edit the repository, never a wiki.
