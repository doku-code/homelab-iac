---
title: Identity and secrets map
description: Who signs in where and through what, and which secret-store path feeds which deployment.
published: true
tags:
- guide
- current
- map
- identity
- secrets
- authentik
- phase
editor: markdown
date: '2026-11-25T00:00:00.000Z'
dateCreated: '2026-11-25T00:00:00.000Z'
---

# Identity and secrets map

> **ID:** GUIDE-map-identity · **Type:** guide · **Status:** current · **Updated:** 2026-11-25 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/hubs/identity-and-secrets-map.md)

## Sign-in

Authentik (<https://auth.doku-lab.net>) signs people in. Git owns the applications, clients and groups
([`services/authentik/blueprints`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/)); Authentik owns the people. A new service
with a web interface gets its blueprint in the change that deploys it; every service keeps its local administrator.

<!-- map:sign-in:start -->
| Blueprint | Application | How |
|---|---|---|
| [`homelab-access.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-access.yaml) |  | shared: groups, outpost |
| [`homelab-argocd.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-argocd.yaml) | <https://argocd.doku-lab.net> | OpenID Connect client |
| [`homelab-grafana.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-grafana.yaml) | <https://grafana.doku-lab.net> | OpenID Connect client |
| [`homelab-headlamp.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-headlamp.yaml) | <https://headlamp.doku-lab.net> | OpenID Connect client |
| [`homelab-homepage.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-homepage.yaml) | <https://home.doku-lab.net> | Authentik in front of the service (forward auth) |
| [`homelab-media.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-media.yaml) | <https://media.doku-lab.net> | Authentik in front of the service (forward auth) |
| [`homelab-netbox.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-netbox.yaml) | <https://netbox.doku-lab.net> | OpenID Connect client |
| [`homelab-outpost.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-outpost.yaml) |  | shared: groups, outpost |
| [`homelab-proxmox.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-proxmox.yaml) | <https://pve-management.doku-lab.net> | OpenID Connect client |
| [`homelab-wiki.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-wiki.yaml) | <https://wiki.doku-lab.net> | OpenID Connect client |
| [`homelab-windmill.yaml`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/services/authentik/blueprints/homelab-windmill.yaml) | <https://windmill.doku-lab.net> | OpenID Connect client |
<!-- map:sign-in:end -->

Check after a change: `scripts/secrets.py run /authentik -- make sso-check`.

## Secrets

Secrets live in Phase and are read through [`scripts/secrets.py`](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/scripts/secrets.py), which puts them in the
environment of one command; they are never written to Git, to a plan or to a log. An age-encrypted recovery bundle
holds the paths needed to rebuild from nothing ([ADR-004](/docs/decisions/adr-004-secrets-phase-runtime-sops-bootstrap)).
The table lists paths, never values.

<!-- map:secret-paths:start -->
| Path in the secret store | Read by |
|---|---|
| `/` | `make homepage-deploy`, `make netbox-discover`, `make observability-deploy` |
| `/authentik` | `make argocd-deploy`, `make authentik-deploy`, `make authentik-status`, `make headlamp-deploy`, `make netbox-deploy`, `make observability-deploy`, `make proxmox-sso`, `make sso-check`, `make wiki-configure`, `make windmill-sso` |
| `/deploy-runner` | `make deploy-runner-configure` |
| `/dns` | `make dns-configure` |
| `/forgejo-runner/connections` | `make ci-runner-configure` |
| `/forgejo-runner/registry` | `make ci-runner-configure` |
| `/homepage` | `make homepage-deploy` |
| `/ingress` | `make ingress-certs-deploy`, `make ingress-tls-deploy` |
| `/k3s` | `make k3s-cluster-configure` |
| `/media` | `make media-configure` |
| `/monitoring` | `make observability-deploy` |
| `/netbox` | `make netbox-apply`, `make netbox-autosync`, `make netbox-deploy`, `make netbox-docs`, `make netbox-export`, `make netbox-identities`, `make netbox-inventory`, `make netbox-plan`, `make netbox-prune`, `make windmill-bootstrap` |
| `/postgresql` | `make authentik-deploy`, `make media-configure`, `make netbox-deploy`, `make observability-deploy`, `make postgresql-configure`, `make vaultwarden-deploy`, `make wiki-deploy`, `make windmill-deploy` |
| `/pve-management` | `make netbox-autosync` |
| `/switch` | `make observability-deploy` |
| `/truenas` | `make observability-deploy` |
| `/wiki` | `make wiki-configure`, `make wiki-deploy`, `make wiki-sync` |
| `/windmill` | `make windmill-bootstrap`, `make windmill-push`, `make windmill-sso` |
<!-- map:secret-paths:end -->

## Credentials that are deliberately narrow

- The OpenTofu token on Proxmox cannot delete files from a datastore.
- The validation runner holds no infrastructure credential ([ADR-008](/docs/decisions/adr-008-workstation-bootstrap-ct301-validation-only)).
- NetBox holds no credential at all ([ADR-016](/docs/decisions/adr-016-netbox-is-the-inventory-and-ipam-source-of-truth-populated-f)).
