---
title: 'TASK-039 — Charcoal Titanium: one design system for the services'' interfaces'
description: Shared design tokens, a static preview, and theme adapters for the services that support safe appearance customization; Homepage first.
published: true
tags:
- task
- in-progress
- theme
- design-system
- homepage
editor: markdown
date: '2026-11-27T00:00:00.000Z'
dateCreated: '2026-11-27T00:00:00.000Z'
---

# TASK-039 — Charcoal Titanium: one design system for the services' interfaces

> **ID:** TASK-039 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-27 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-039-charcoal-titanium-one-design-system-for-the-services-interfa.md)

## Goal

One visual identity ("Charcoal Titanium") across the services that support safe appearance customization, without
replacing an application or changing the platform: shared tokens, a static preview, and one adapter per eligible
service. Operator's brief of 2026-11-27.

## Context

- [Guide](/docs/guides/charcoal-titanium-the-shared-design-system-and-each-service): the pieces, the
  compatibility matrix, deployment and undo, what depends on upstream.
- Homepage's visual layer and its `custom.js` contracts: [TASK-027](/tasks/task-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab).
- Forgejo is the operator's TrueNAS app: only its theme is installed (`services/forgejo/install-theme.py`, allowed on 2026-11-27).

## Acceptance criteria

- [x] One source of tokens; every other form is generated and checked (`make theme`, `make theme-check`, CI).
- [x] A static preview with navigation, table, actions, form controls, dialog, menu, states, metric cards, a graph, code and a sign-in page.
- [x] Homepage restyled with every widget kept; a plain charcoal page, no background image.
- [x] Adapters through each application's own mechanism: Authentik (brand CSS), Argo CD (`configs.styles`), Forgejo (theme file), AdGuard Home (dark).
- [x] Compatibility matrix, deployment and undo instructions.
- [ ] Deployed and looked at live: Homepage, Authentik and Forgejo are (2026-11-27); Argo CD and AdGuard Home are not.

## Verification

```
make theme-check
make homepage-k3s-check
make authentik-check
make argocd-check
make dns-check
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| `tests/theme.py` | palette is neutral and readable, generated copies match the source, adapters hold no hand-written colours and call no other site, Homepage's selectors, Authentik's and Argo CD's mechanisms, Forgejo's variable names, the preview | `make theme-check` | PASS (2026-11-27) |
| `tests/homepage-k3s.py` | configuration digest, cards and data sources | `make homepage-k3s-check` | PASS (2026-11-27) |
| `tests/authentik.py` | every blueprint in the ConfigMap, nothing deleted, clients unchanged | `make authentik-check` | PASS (2026-11-27) |
| `tests/argocd.py`, `tests/dns.py` | chart values, AdGuard template | `make argocd-check`, `make dns-check` | PASS (2026-11-27) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Audit | Homepage v2.8.0, Authentik 2026.8.5, Argo CD chart 10.18.1, Grafana chart 14.5.0, NetBox v4.7.5, Wiki.js 3.5.0, Windmill 1.876.1, Vaultwarden 1.37.2, Headlamp 0.46.0, Forgejo 17.0.1 (TrueNAS) | pinned versions in the repository, Forgejo's API | 2026-11-27 |
| Authentik's mechanism | the running version's brand model has `branding_custom_css` and `attributes`; its stylesheets define the `--pf-global--*` and `--ak-*` variables the adapter sets, for `html[data-theme=dark]` and `:host([theme="dark"])` | `ak shell`, `/web/dist/styles` in the pod (read only) | 2026-11-27 |
| Argo CD's mechanism | `helm template` with our values: ConfigMap `argocd-styles-cm`, mount `/shared/app/custom`, `ui.cssurl: ./custom/custom.styles.css` | chart 10.18.1 | 2026-11-27 |
| Forgejo's mechanism | the installed dark theme is built on a `--steel-*` ramp and `--color-primary*`; the theme sets 57 variables, all of that list but the font hook | `theme-forgejo-dark.css` of the live instance (read) | 2026-11-27 |
| Preview, seen | renders as intended at 1440 px | headless browser screenshot, `.local/theme-shots/preview.png` | 2026-11-27 |
| Homepage, seen locally | a local Homepage v2.8.0 with our configuration and a copy of the live widget data: header summary, 30 cards, node, k3s, PostgreSQL, TrueNAS, qBittorrent and Plex widgets all drawn | `.local/theme-shots/homepage-widgets.png` | 2026-11-27 |
| Forgejo, live | theme installed by `services/forgejo/install-theme.py`; Forgejo answers, 8 repositories of the same total size before and after, the explore page rendered in the theme | headless screenshot `.local/theme-shots/forgejo-live.png` | 2026-11-27 |
| Homepage and Authentik, live | pushed; the operator found Homepage flat and Authentik's application search field bent, the admin interface fine. Second pass: icon wells, figures in one strip, status chips, stronger type, larger type on wide screens; a rule for the search field | local screenshot `.local/theme-shots/hp-after.png`; the search field's correction **not seen** | 2026-11-27 |
| Authentik's sign-in page, seen locally | the live page served through a local preview with the stylesheet where the brand's CSS goes: with variables alone the page and card shared one tone, the button label was unreadable and the field was an underline; with the rules, a bordered card on the canvas, an off-white button with dark text, a boxed field | `.local/theme-shots/ak-login.png` | 2026-11-27 |
| Argo CD, AdGuard Home rendered | deployed (2026-11-27); **not seen rendered** by the agent (signed-in pages); the operator found Argo CD nearly stock, its adapter was rewritten against the rules of v3.6.1 | | 2026-11-27 |
| Forgejo: mark, links, contribution counts | new mark and underlined links seen rendered with an empty browser profile; the counts file went from "generated 2026-09-10, 330" to the minute of the run, 962 contributions over 87 days, today included; two runs of the cron job succeeded | `.local/theme-shots/forgejo-md2.png`, TrueNAS job states | 2026-11-28 |
| Background images removed from Homepage (operator, 2026-11-27) | switcher, layer, volume, mount and `make homepage-images` gone from the files; `make homepage-k3s-check` PASS. The volume `homepage-images` (7.4 MiB of images) is still in the cluster | | 2026-11-27 |
| Keyboard focus, reduced motion, responsive layout | rules are in the stylesheets and the preview; **not tested in a browser by hand** | | 2026-11-27 |

## Completion summary

Remaining: the operator's look at each interface after the last changes (dot grid, Authentik's application icons, Argo CD
rule for rule, NetBox's plugin, Forgejo's mark, links and contribution counts). Not seen rendered by the agent:
Argo CD, NetBox, Authentik's signed-in interfaces.
