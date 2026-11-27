# Forgejo: the Charcoal Titanium theme

Forgejo runs as a TrueNAS app and is not deployed from this repository (operator: "leave my forgejo alone"). This
directory only holds a theme file made for the installed version (17.0.1) and how to install it by hand.

1. Copy `theme-charcoal-titanium.css` into Forgejo's custom directory: `<custom>/public/assets/css/` (on the NAS,
   under the app's data dataset; `<custom>` is shown in Site administration > Configuration as "Custom file root path").
2. In `app.ini`, section `[ui]`, add the theme to the list, and make it the default if wanted:

   ```ini
   [ui]
   THEMES = forgejo-auto,forgejo-light,forgejo-dark,gitea-auto,gitea-light,gitea-dark,forgejo-auto-deuteranopia-protanopia,forgejo-light-deuteranopia-protanopia,forgejo-dark-deuteranopia-protanopia,forgejo-auto-tritanopia,forgejo-light-tritanopia,forgejo-dark-tritanopia,charcoal-titanium
   DEFAULT_THEME = charcoal-titanium
   ```

3. Restart Forgejo. Each user picks the theme in Settings > Appearance; `DEFAULT_THEME` only applies to visitors and
   new accounts.

To undo: remove the name from `THEMES`, restore `DEFAULT_THEME`, restart, delete the file.

The theme imports Forgejo's own dark theme and only replaces its grey ramp and its primary colour, so an update of
Forgejo keeps working as long as `theme-forgejo-dark.css` keeps its `--steel-*` and `--color-primary*` variables
(`make theme-check` compares the names this file sets with `forgejo-17.0.1-dark-variables.txt`, the list taken from the
installed version; refresh that list when Forgejo is upgraded).
