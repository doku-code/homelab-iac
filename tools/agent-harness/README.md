# agent-harness (vendored)

The `harness` CLI used by this repository (`harness check`, `harness status`, `harness docs index`),
vendored so that the repository, its CI and any recovery workstation can install it without access
to the upstream template repository.

| Item | Value |
|------|-------|
| Upstream | `doku-code/agent-harness` (operator's template repository) |
| Version | 0.1.0, upstream commit `8ddf06d81f71577aaf7c6ce93839c628270670f8` |
| Vendored | 2026-11-14; `harness/` is byte-identical to that commit |
| Contents | `harness/` package (with its assets), `pyproject.toml`, `LICENSE` (MIT) — no tests or template docs |
| Install | `.venv/bin/python -m pip install -r requirements-agents.txt` (installs this directory) |

This is agent tooling only: deployment and recovery of the homelab never depend on it.

## Updating

1. Replace `harness/`, `pyproject.toml` and `LICENSE` with the new upstream version; do not edit them here.
2. Update the version and commit in this file.
3. Reinstall, then run `.venv/bin/harness update --diff` and review the managed-file changes
   (`harness-docs-validate.yml` is intentionally adapted and reported as a conflict).
4. Run `.venv/bin/harness check` and the repository verification commands.
