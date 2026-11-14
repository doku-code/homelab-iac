# .local/ — ignored local artifacts

This directory is excluded from Git by the harness-managed `.gitignore` block. Use it for:

- temporary credentials and tokens an agent was explicitly authorised to use
- sensitive reports, unredacted debug output, private investigation artifacts
- local execution state and temporary configuration

Nothing here is ever published by `harness docs export-wiki` or indexed by `harness docs index`.

## Sanitised variables convention

Commit a `vars.example.yaml` (names, types, descriptions, dummy values, secret-provider references) and keep the
real `vars.yaml` here:

```yaml
# vars.example.yaml — committed
api_base_url: "https://api.example.test"      # string, required
api_token: "<from secret provider: PROJECT_API_TOKEN>"   # secret, never committed
db_password: "changeme"                        # secret, placeholder only
```

Documentation refers to the mechanism ("token supplied through the authorised local configuration"), never the
value. Delete temporary sensitive artifacts when they are no longer needed.
