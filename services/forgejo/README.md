# Forgejo: the Charcoal Titanium theme

Forgejo runs as a TrueNAS catalog app and is not deployed from this repository. The operator allowed its theme to be
installed (2026-11-27); nothing else of the app is managed here.

`install-theme.py` does it and can be run again (after a change of the theme, or after an update of Forgejo):

```
scripts/secrets.py run /truenas -- services/forgejo/install-theme.py                              # reports only
FORGEJO_THEME_APPROVED=yes scripts/secrets.py run /truenas -- services/forgejo/install-theme.py   # does it
```

1. It writes `theme-charcoal-titanium.css` into Forgejo's custom directory (`custom/public/assets/css/` under the
   app's data path), beside the operator's own files.
2. It adds `FORGEJO__ui__THEMES` (Forgejo's themes plus this one) and `FORGEJO__ui__DEFAULT_THEME` to the app's extra
   environment variables; TrueNAS redeploys the app and Forgejo writes them into `app.ini` when it starts.

`DEFAULT_THEME` applies to visitors and to accounts that never chose a theme; anyone else picks "charcoal-titanium"
in Settings > Appearance.

To undo: the same command with `undo` removes the two variables; the file stays and does nothing.

The theme imports Forgejo's own dark theme and only replaces its grey ramp and its primary colour, so an update of
Forgejo keeps working as long as `theme-forgejo-dark.css` keeps its `--steel-*` and `--color-primary*` variables
(`make theme-check` compares the names this file sets with `forgejo-17.0.1-dark-variables.txt`, the list taken from the
installed version; refresh that list when Forgejo is upgraded).
