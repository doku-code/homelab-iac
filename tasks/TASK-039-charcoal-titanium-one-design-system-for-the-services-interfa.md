---
id: TASK-039
title: "Charcoal Titanium: one design system for the services' interfaces"
summary: Shared design tokens, a static preview, and theme adapters for the services that support safe appearance customization; Homepage first.
type: task
status: in-progress
priority: medium
milestone: M010
created: 2026-11-27
updated: 2026-11-27
tags: [theme, design-system, homepage]
depends_on: []
related: [GUIDE-charcoal-titanium-the-shared-design-system-and-each-service, TASK-027]
related_decisions: []
related_implementations: [scripts/theme.py, services/_shared/theme/tokens.json, services/homepage/config/custom.css, services/authentik/theme.css, services/argocd/theme.css, services/forgejo/theme-charcoal-titanium.css]
related_tests: [tests/theme.py, tests/homepage-k3s.py, tests/authentik.py, tests/argocd.py, tests/dns.py]
tests_justification: ""
verification_commands: [make theme-check, make homepage-k3s-check, make authentik-check, make argocd-check, make dns-check]
evidence: []
---

<!--
Task: the operational unit that guides an agent through one implementation step.
Create when: work spans a session boundary or needs explicit verification evidence.
Status vocabulary: planned | in-progress | blocked | completed | cancelled.
Rules:
- Never mark completed without evidence (command output, test result, commit).
- If a command failed, record the failure. If nothing was verified, write "not verified".
- Keep summaries proportional: a small task needs two factual sentences, not a log.
- A feature or fix ships with its tests in the project's test framework, written in this task and listed in
  `related_tests`. If no test is possible, say why in `tests_justification`; `harness check` refuses a completed
  task that has implementation paths but neither.
-->

# Charcoal Titanium: one design system for the services' interfaces

## Goal

One visual identity ("Charcoal Titanium") across the services that support safe appearance customization, without
replacing an application or changing the platform: shared tokens, a static preview, and one adapter per eligible
service. Operator's brief of 2026-11-27.

## Context

- [Guide](../docs/guides/charcoal-titanium-the-shared-design-system-and-each-service.md): the pieces, the
  compatibility matrix, deployment and undo, what depends on upstream.
- Homepage's visual layer and its `custom.js` contracts: [TASK-027](TASK-027-homepage-on-k3s-behind-authentik-rearranged-for-the-doku-lab.md).
- Forgejo is the operator's TrueNAS app and is left alone: a theme file and its installation steps only.

## Acceptance criteria

- [x] One source of tokens; every other form is generated and checked (`make theme`, `make theme-check`, CI).
- [x] A static preview with navigation, table, actions, form controls, dialog, menu, states, metric cards, a graph, code and a sign-in page.
- [x] Homepage restyled with every widget kept; a plain charcoal page, no background image.
- [x] Adapters through each application's own mechanism: Authentik (brand CSS), Argo CD (`configs.styles`), Forgejo (theme file), AdGuard Home (dark).
- [x] Compatibility matrix, deployment and undo instructions.
- [ ] Deployed and looked at live (needs the operator's go: a push deploys Homepage and Authentik).

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
| Forgejo, seen locally | **not verified**: the local image could not be pulled in time | | 2026-11-27 |
| Authentik's sign-in page, seen locally | the live page served through a local preview with the stylesheet where the brand's CSS goes: with variables alone the page and card shared one tone, the button label was unreadable and the field was an underline; with the rules, a bordered card on the canvas, an off-white button with dark text, a boxed field | `.local/theme-shots/ak-login.png` | 2026-11-27 |
| Authentik's application list and admin interface, Argo CD, AdGuard Home rendered | **not verified**: they need a signed-in session or a deployment | | 2026-11-27 |
| Background images removed from Homepage (operator, 2026-11-27) | switcher, layer, volume, mount and `make homepage-images` gone from the files; `make homepage-k3s-check` PASS. The volume `homepage-images` (7.4 MiB of images) is still in the cluster | | 2026-11-27 |
| Keyboard focus, reduced motion, responsive layout | rules are in the stylesheets and the preview; **not tested in a browser by hand** | | 2026-11-27 |

## Completion summary

Remaining: the operator's go to push (Homepage and Authentik go live with it), `make argocd-deploy` and
`make dns-configure` for the two others, the Forgejo theme by hand; then a look at each live interface and
corrections. Fonts are not self-hosted yet (Geist and Inter are used only where a device has them).
