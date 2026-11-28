# Forgejo: the Charcoal Titanium theme

Forgejo runs as a TrueNAS catalog app and is not deployed from this repository. The operator allowed its theme to be
installed (2026-11-27); nothing else of the app is managed here.

`install-theme.py` does it and can be run again (after a change of the theme, or after an update of Forgejo):

```
scripts/secrets.py run /truenas -- services/forgejo/install-theme.py                              # reports only
FORGEJO_THEME_APPROVED=yes scripts/secrets.py run /truenas -- services/forgejo/install-theme.py   # does it
```

1. It writes into Forgejo's custom directory, beside the operator's own files: the theme
   (`public/assets/css/theme-charcoal-titanium.css`), the mark (`public/assets/img/logo.svg`, `favicon.svg`,
   `favicon.png`, drawn for this theme: a rounded diamond with a branch cut out) and `scripts/contributions.sh`.
2. It adds `FORGEJO__ui__THEMES` (Forgejo's themes plus this one) and `FORGEJO__ui__DEFAULT_THEME` to the app's extra
   environment variables; TrueNAS redeploys the app and Forgejo writes them into `app.ini` when it starts.
3. It keeps one cron job on the NAS (System > Advanced > Cron Jobs) that runs `contributions.sh` inside Forgejo's
   container every ten minutes, one run at a time.

## The contribution grid of the profile page

Forgejo's own heatmap shows a visitor the public activity only. The operator's page script
(`public/assets/js/doku-code-contributions.js`, theirs, not in this repository) draws a grid from
`public/assets/aymerick/contributions-doku-code.json`. That file was only ever written by hand, by a generator that
started several processes per commit and needed more than ten minutes for one run. `contributions.sh` replaces the
generator, not the page script: it reads each repository once, counts a commit once however many repositories hold
it, and writes the same file (dates and counts only) in under a second. It takes the account's address from Forgejo
itself; other names or addresses the commits carry go, one per line, into `custom/scripts/contributions.identities` on
the NAS (never into Git).

Browsers keep Forgejo's files for some hours: after a change of the theme or the mark, reload without the cache.

`DEFAULT_THEME` applies to visitors and to accounts that never chose a theme; anyone else picks "charcoal-titanium"
in Settings > Appearance.

To undo: the same command with `undo` removes the two variables and the cron job; the files stay and do nothing
(delete `public/assets/img/` to get Forgejo's own mark back).

The theme imports Forgejo's own dark theme and only replaces its grey ramp and its primary colour, so an update of
Forgejo keeps working as long as `theme-forgejo-dark.css` keeps its `--steel-*` and `--color-primary*` variables
(`make theme-check` compares the names this file sets with `forgejo-17.0.1-dark-variables.txt`, the list taken from the
installed version; refresh that list when Forgejo is upgraded).
