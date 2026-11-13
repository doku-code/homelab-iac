# homelab-iac

Infrastructure as Code for a self-hosted homelab that is being rebuilt into a reproducible,
automated platform: OpenTofu provisions Proxmox guests, Ansible configures them, Docker Compose
runs services, Forgejo holds the source of truth and runs CI, and Windmill provides forms and
schedules that trigger the same versioned workflows.

The rebuild is **rolling**: the running homelab provisions its replacement, services move one at
a time with validation and rollback, and emptied machines are reinstalled and joined. The first
new node, `pve-management`, is a standalone bootstrap and recovery host.

## Start here

| Need | Document |
|------|----------|
| Vision, strategy, repository map | [docs/project-overview.md](docs/project-overview.md) |
| Target architecture and layer ownership | [docs/architecture/platform.md](docs/architecture/platform.md) |
| Decisions | [docs/decisions/](docs/decisions/) |
| Roadmap and progress | [docs/dashboard.md](docs/dashboard.md), [milestones/](milestones/), [tasks/](tasks/) |
| What exists today (legacy, unverified) | [docs/investigations/legacy-inventory.md](docs/investigations/legacy-inventory.md) |
| Previous workflow, runbooks and evidence | [docs/archive/codex-2026/](docs/archive/codex-2026/README.md) |

Agent instructions: [AGENTS.md](AGENTS.md) (Codex and others), [CLAUDE.md](CLAUDE.md) (Claude Code).

## Controller setup

```bash
make setup-controller
```

```bash
.venv/bin/python -m pip install -r requirements-agents.txt
```

```bash
.venv/bin/harness status
```

Secrets are never committed. Infisical supplies runtime secrets today; Phase and SOPS + age are
the target ([ADR-004](docs/decisions/ADR-004-secrets-phase-runtime-sops-bootstrap.md)).

## Legacy implementation

`terraform/stacks/`, `ansible/`, `services/`, `gitops/`, `scripts/`, `tests/` and the `Makefile`
still manage live resources and keep working as before; several Terraform roots hold their only
state as local files beside the code. They are migrated or retired service by service
([ADR-007](docs/decisions/ADR-007-archive-legacy-workflow-keep-live-roots.md)).
