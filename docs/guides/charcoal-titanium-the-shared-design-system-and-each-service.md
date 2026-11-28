---
title: Charcoal Titanium
description: The design tokens, the preview, what each service takes from them and how, how to change, deploy and undo a theme.
published: true
tags:
- guide
- current
- theme
- design-system
editor: markdown
date: '2026-11-27T00:00:00.000Z'
dateCreated: '2026-11-27T00:00:00.000Z'
---

# Charcoal Titanium

> **ID:** GUIDE-charcoal-titanium-the-shared-design-system-and-each-service · **Type:** guide · **Status:** current · **Updated:** 2026-11-27 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/guides/charcoal-titanium-the-shared-design-system-and-each-service.md)

One visual identity for the services' interfaces: neutral charcoal surfaces with a slight warmth, off-white primary
actions, fine borders, compact type, and colour only where it means something (states, data series, logos, syntax).
Each application keeps its own interface; an *adapter* maps the application's native theme variables to the shared
tokens. Where an application has no supported way in, its own dark mode is left alone.

## The pieces

| Piece | Path | Edited by hand |
|---|---|---|
| Tokens, the one source | `services/_shared/theme/tokens.json` | yes |
| Tokens as CSS | `services/_shared/theme/tokens.css` | no, `make theme` |
| Preview, the visual contract | `services/_shared/theme/preview/index.html` (open the file in a browser) | yes |
| Adapter stylesheets | beside each application (table below); the token block at their top is written by `make theme` | yes, below the block |
| Copies inside deployment files | Authentik's blueprint, Argo CD's values | no, `make theme` |
| Generator and tests | `scripts/theme.py`, `tests/theme.py` (`make theme-check`, also in CI) | |

Kustomize cannot read outside an application's directory and nothing serves theme files at run time, so the
tokens are **copied** into each adapter by the generator. `make theme-check` fails when a copy is stale.

To change a colour for everything: edit `tokens.json`, `make theme`, `make homepage-k3s-check` (it prints the new
`config-digest` to put in `services/homepage/deployment.yaml`), commit.

## Compatibility matrix

| Application | Customization mechanism | Files changed | Customization scope | Validation status | Limitations |
|---|---|---|---|---|---|
| Homepage v2.8.0 | its own `custom.css`, `custom.js`, `settings.yaml` | `services/homepage/config/custom.css`, `custom.js`, `settings.yaml`, `deployment.yaml` (digest) | **fully themed**: page, header, search, groups, cards, every injected widget, charts | tests pass; seen in a local Homepage with a copy of the live widget data (screenshot); live since 2026-11-27, looked at by the operator | Geist ships inside `custom.css` (`services/_shared/theme/fonts`, SIL Open Font License, written in by `make theme`); the other adapters use it only when the device has it |
| Authentik 2026.8.5 | the brand's custom CSS and theme setting, by blueprint | `services/authentik/theme.css`, `blueprints/homelab-brand.yaml`, `kustomization.yaml` | **themed**: variables for every surface, line, text and action, and rules for the sign-in card, buttons, fields, cards, dialogs and menus | live since 2026-11-27; sign-in page seen rendered; the operator looked at the application list (its search field was bent, corrected by a rule of its own, **the correction not seen**) and the admin interface (fine) | rules name PatternFly classes, which a new Authentik may rename; a user who chose the light mode gets the same dark colours |
| Argo CD (chart 10.18.1) | `configs.styles` of the chart (its documented custom stylesheet) | `services/argocd/theme.css`, `values.yaml` | **partially themed**: sidebar, buttons, links, focus ring; health, sync and graph colours untouched | chart renders the ConfigMap, the mount and `ui.cssurl`; **not seen rendered** | class names are argo-ui's and not a published contract; dark or light is each user's own choice in Argo CD |
| Forgejo 17.0.1 (TrueNAS app) | a custom theme file and `[ui] THEMES` | `services/forgejo/theme-charcoal-titanium.css`, `README.md`, the list of the installed version's variables | **themed**, the default theme for visitors and new accounts: every surface, line, text and primary colour; diffs, syntax, states and labels are Forgejo's | variable names checked against the installed version's dark theme; installed on 2026-11-27 and the public pages seen rendered; the same 8 repositories before and after | Forgejo is not deployed from this repository: `services/forgejo/install-theme.py` puts the file and two settings into the NAS's app; an account that already chose a theme keeps it until changed in Settings > Appearance |
| AdGuard Home v0.107.79 | `theme` of its configuration file | `ansible/roles/adguard_home/templates/AdGuardHome.yaml.j2` | **native theme only**: dark instead of following the browser | template test; applied at the next `make dns-configure` | no custom colours exist in AdGuard Home |
| Grafana (chart 14.5.0, OSS) | none beyond its dark default | none | **native theme only**; the provisioned dashboards keep Grafana's palette | already dark | custom themes and branding are Grafana Enterprise features |
| Phase 1.0.2 | none | none | **left as it is**: it is one of the references of this design | | no supported theming; the password-policy patch is not a place for cosmetics |
| Headlamp 0.46.0 | per-user theme in its settings | none | **native theme only** | | a custom theme needs a compiled plugin: not worth a build pipeline |
| NetBox v4.7.5 | a plugin of three files (`netbox_charcoal_titanium`, a ConfigMap) that adds one stylesheet to the head of every page through `PluginTemplateExtension.head` | `services/netbox/theme.css`, `access.yaml` (ConfigMap `netbox-theme`), `values.yaml` (mount, `PYTHONPATH`, `plugins`) | **themed** in dark mode: Tabler's variables for surfaces, lines, text and the accent, the cards and the side menu NetBox paints itself, the dot grid | tests pass; **not seen rendered** | the light mode is NetBox's own: each user picks dark in their preferences; a new NetBox may rename `--tblr-*` variables |
| Wiki.js 3.5.0 | site theme in its administration (stored in its database) | none | **native theme only** | | not declarative from this repository |
| Windmill CE 1.876.1 | per-user dark mode | none | **native theme only** | | branding is an Enterprise feature |
| Vaultwarden 1.37.2 | per-user theme of the web vault | none | **native theme only** | | a stylesheet override exists but a password vault is not themed for looks |
| Nextcloud, qBittorrent (VueTorrent), Plex | their own appearance settings | none | **unchanged** | not verified | TrueNAS apps outside this repository's deployment; Plex has no theming |
| Proxmox, TrueNAS, pfSense, the switch | per-user or vendor themes | none | **unchanged** | | appliance interfaces are not modified |

## Deploy and undo

Nothing is live until the branch is pushed: Argo CD follows `main`.

| Adapter | Goes live with | Undo |
|---|---|---|
| Homepage | the push (Argo CD application `homepage`; the digest restarts the pod). The background images are gone from the page; their volume `homepage-images` stays in the cluster until someone deletes it (the application does not prune) | `git revert` of the commits |
| Authentik | the push (ConfigMap `authentik-blueprints`; the worker applies blueprints within the hour, or at once from Customisation > Blueprints) | remove `blueprints/homelab-brand.yaml` from `kustomization.yaml`, then empty "Custom CSS" and the theme attribute of the default brand in the admin interface (a blueprint that is removed does not undo itself) |
| Argo CD | `scripts/secrets.py run /authentik -- make argocd-deploy ARGOCD_DEPLOY_APPROVED=yes` (Argo CD is installed by Make, not by itself) | remove `configs.styles` from `values.yaml`, same target |
| AdGuard Home | `scripts/secrets.py run /dns -- make dns-configure DNS_CONFIGURE_APPROVED=yes` | `theme: auto` in the template, same target |
| Forgejo | `FORGEJO_THEME_APPROVED=yes scripts/secrets.py run /truenas -- services/forgejo/install-theme.py` (theme, mark, contribution counts; restarts Forgejo only when its settings change) | the same command with `undo` |
| NetBox | the push (Argo CD application `netbox`; the pods restart once for the new mount, later changes of the stylesheet show without a restart) | remove `netbox_charcoal_titanium` from `plugins` in `values.yaml` |

Each adapter stands alone: any one can be left out or undone without the others.

## When an application is updated

| Adapter | Depends on | If it changes upstream |
|---|---|---|
| Homepage | Homepage's element ids (`#information-widgets`, `.service-card`, …) and its `custom.css` hook | cards fall back to Homepage's look; the widgets are ours |
| Authentik | PatternFly variable and class names (`--pf-global--…`, `.pf-c-login__main`, `.pf-c-button`, `.pf-c-form-control`) and the brand's `branding_custom_css` field | a renamed variable or class is ignored and Authentik's own look shows there; the rules hide, move and add nothing (`tests/theme.py`), so a sign-in step cannot disappear |
| Argo CD | `.sidebar`, `.argo-button--base`, `.argo-button--base-o` | the rule stops applying; nothing breaks |
| NetBox | Tabler's `--tblr-*` variables, `html[data-bs-theme=dark]`, the plugin hook `head()` | a renamed variable is ignored and NetBox's colour shows there; if the hook goes, NetBox refuses the plugin at start: remove it from `plugins` |
| Forgejo | `--steel-*` and `--color-primary*` of `theme-forgejo-dark.css` | refresh `forgejo-17.0.1-dark-variables.txt` from the new version; `make theme-check` names what no longer exists |

## What was looked at, and how

- Static: `make theme-check`, `make homepage-k3s-check`, `make authentik-check`, `make argocd-check`, `make dns-check`.
- Rendered manifests: the Argo CD chart with our values (stylesheet ConfigMap, mount, `ui.cssurl`).
- Local visual: the preview and a local Homepage v2.8.0 with our configuration and a copy of the live widget data,
  screenshots with a headless browser.
- Live: Homepage and Authentik by the operator (2026-11-27), Forgejo's public pages by a headless screenshot. Argo CD and
  AdGuard Home are not deployed yet.
