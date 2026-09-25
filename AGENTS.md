# Homelab IaC — Agent Instructions

## Project Mission

This repository defines and automates a self-hosted homelab infrastructure.

The long-term goal is to make the infrastructure as reproducible as reasonably possible:

- infrastructure resources should be declarative;
- host configuration should be automated;
- application configuration should be versioned;
- secrets must remain outside Git;
- rebuilding or migrating a service should require minimal undocumented manual work.

Prefer maintainable, understandable, and boring solutions over clever ones.

The repository is public. Treat every committed file as world-readable.

## Repository Boundary

Codex's default authorized scope is this `homelab-iac` repository only.
Access to sibling repositories requires explicit per-repository, per-task
authorization. Filesystem access or architectural relevance is not
authorization. Never operate on multiple repositories simultaneously.


## Engineering Principles

### Keep responsibilities clear

Use the existing ownership model:

- Terraform:
  - infrastructure resources;
  - VMs and infrastructure-level configuration;
  - declarative resource lifecycle;
  - importing existing infrastructure when appropriate.

- Ansible:
  - operating system configuration;
  - package installation;
  - host configuration;
  - configuration deployment;
  - post-provisioning tasks.

- Docker Compose:
  - application/service composition;
  - container configuration;
  - local service dependencies.

- Infisical:
  - secrets;
  - credentials;
  - tokens;
  - runtime secret retrieval.

- Makefile:
  - human-facing workflows;
  - common commands;
  - hiding repetitive implementation details.

Do not blur these responsibilities without a strong reason.


### Prefer simple architecture

Prefer:

- obvious directory structures;
- small modules with clear purposes;
- explicit configuration;
- standard tooling;
- predictable workflows;
- reusable patterns where reuse is real.

Avoid:

- unnecessary abstraction;
- premature frameworks;
- deep module hierarchies;
- wrappers around wrappers;
- generic systems built for hypothetical future requirements.

Do not create an abstraction just because two files look similar.

Rule of thumb:

> Abstract repeated concepts, not imagined future repetition.


### Future-proof without over-engineering

Architecture should make future changes easier without making the current system harder to understand.

When choosing between approaches, prefer the one that:

1. has a clear ownership boundary;
2. has fewer hidden dependencies;
3. can be reproduced from the repository;
4. is easy for another engineer to understand;
5. is easy to replace later;
6. does not unnecessarily lock the project into one implementation.

Favor incremental improvements over large rewrites.


## Repository Safety

### Public repository

Never commit:

- passwords;
- API tokens;
- access tokens;
- refresh tokens;
- webhook URLs;
- private keys;
- Machine Identity client secrets;
- `.env` files containing secrets;
- Terraform state;
- Terraform plans containing sensitive information;
- private `tfvars`;
- secret exports;
- credential caches.

Before committing, inspect the staged diff.

Do not assume private IP addresses are secrets, but avoid exposing unnecessary identifying infrastructure details.


### Infrastructure safety

Treat this homelab as production-like infrastructure.

Do not perform destructive or disruptive actions without explicit approval.

Never automatically run:

- `terraform apply`;
- `terraform destroy`;
- destructive Proxmox commands;
- VM deletion;
- storage deletion;
- network reconfiguration;
- firewall changes;
- credential rotation;
- cluster-wide changes.

Planning, validation, syntax checking, and read-only inspection are allowed unless the task states otherwise.

Prefer read-only validation before mutation.


### Critical workloads

Some nodes run critical or latency-sensitive workloads.

Avoid:

- broad restart operations;
- unnecessary host reboots;
- indiscriminate backup jobs;
- cluster-wide experiments;
- high-impact network tests.

Use `pve-lab` as the preferred experimentation and workbench environment when possible.


## Reproducibility

Manual configuration should gradually be converted into code when it provides real value.

When discovering an undocumented manual dependency:

1. understand it first;
2. determine which tool should own it;
3. automate it in the appropriate layer;
4. document any remaining manual prerequisite.

Do not blindly automate unknown existing state.


### Source of truth

Avoid defining the same configuration in multiple places.

Prefer one source of truth for each concern.

Examples:

- Terraform owns infrastructure resource definitions.
- Ansible owns host configuration.
- Infisical owns secrets.
- Docker Compose owns container topology.
- Git owns non-secret configuration.


## Ansible

Use the repository controller environment.

Prefer:

    .venv/bin/ansible-playbook

or an existing Makefile target.

Do not depend on globally installed Ansible when the repository controller environment is available.

Ansible dependencies belong in:

- `requirements-controller.txt`
- `collections/requirements.yml`

After Ansible changes, run appropriate validation such as:

    .venv/bin/ansible-playbook <playbook> --syntax-check

Use `--check --diff` when it is meaningful and safe.

Secrets should be retrieved from Infisical rather than committed or duplicated in configuration files.

Use `no_log: true` for tasks that may expose secret values.


## Terraform

Keep Terraform roots and states intentionally separated.

All `.tf` files in a Terraform directory belong to the same root module unless explicitly structured otherwise.

Before considering Terraform work complete, run:

    terraform fmt
    terraform validate

Run `terraform plan` when credentials and connectivity are available.

Do not run `terraform apply` unless explicitly authorized.

Avoid `-target` during normal workflows.

Use `-target` only for exceptional recovery or migration cases.

Use imports when adopting existing infrastructure rather than recreating resources unnecessarily.


## Docker and Services

Keep application state external to containers where practical.

Prefer:

- explicit volumes;
- persistent datasets;
- versioned Compose configuration;
- configuration files committed to Git;
- secrets injected at runtime.

Avoid baking environment-specific secrets into images.

Design services so future migration to another host is straightforward.


## Makefile

The Makefile is the preferred operator interface.

When a workflow requires several repetitive commands, expose a clear Make target instead of requiring the operator to memorize them.

Examples:

    make deploy-monitoring
    make workstations-plan
    make workstations-apply
    make workstations-check

Make targets should:

- have predictable names;
- fail clearly;
- avoid destructive surprises;
- use repository-local dependencies;
- reuse existing targets where reasonable.

Do not turn the Makefile into a large application.


## Changes and Refactoring

Before modifying code:

1. inspect the existing implementation;
2. understand which tool currently owns the behavior;
3. preserve working behavior unless the task intentionally changes it.

Prefer modifying existing patterns over introducing parallel patterns.

When refactoring:

- keep behavior stable;
- validate before and after;
- remove obsolete code when safe;
- avoid leaving two competing workflows behind.

Do not perform unrelated cleanup inside a focused change.


## Validation

Before considering work complete, run relevant checks.

At minimum:

    git diff --check

Depending on the change, also use:

- Terraform `fmt`;
- Terraform `validate`;
- Terraform `plan`;
- Ansible `--syntax-check`;
- Ansible `--check --diff`;
- Docker Compose config validation;
- application-specific validation tools.

Report which validations were run and their results.

Do not claim something was tested if it was not.


## Git and Commit Convention

Use Conventional Commit-style messages:

    type(scope): concise description

Examples:

    feat(monitoring): add TrueNAS telemetry alerts
    fix(ansible): remove temporary secret file after deploy
    refactor(iac): unify Infisical authentication workflow
    chore(controller): pin Ansible dependencies
    docs(iac): document workstation deployment workflow

Preferred types:

- `feat`
- `fix`
- `refactor`
- `chore`
- `docs`
- `test`

Use a meaningful scope whenever possible.

Common scopes include:

- `monitoring`
- `terraform`
- `ansible`
- `workstations`
- `controller`
- `infisical`
- `proxmox`
- `storage`
- `network`
- `ci`


### Commit discipline

Prefer several small, logical, and complete commits over one large mixed commit.

Each commit should:

- represent one coherent change;
- leave the repository in a valid state;
- include directly related configuration and documentation;
- be understandable independently;
- avoid unrelated formatting or cleanup.

Good examples:

    chore(controller): add reproducible Ansible environment
    feat(infisical): add machine identity authentication
    refactor(monitoring): use Infisical secrets directly from Ansible

Bad example:

    update homelab stuff

Avoid one giant commit that mixes:

- authentication changes;
- Terraform refactors;
- monitoring dashboards;
- documentation;
- unrelated formatting.

If a task naturally contains several logical milestones, create separate commits.

Do not combine independent changes merely because they were completed in the same working session.


## Formatting

Do not reformat unrelated files.

Preserve the existing style unless improving it is part of the task.

Formatting-only changes should generally be isolated from behavioral changes when they create substantial diff noise.


## Documentation

Document things that would otherwise require rediscovery.

Prioritize:

- architecture decisions;
- non-obvious constraints;
- bootstrap procedures;
- disaster recovery prerequisites;
- external/manual dependencies;
- operator workflows.

Avoid documentation that merely repeats obvious code.

Follow the documentation maintenance contract in
[tasks/README.md](tasks/README.md#contrat-de-maintenance). Maintain the active
task's acceptance evidence, status, dependencies and blockers during work.
Before completion, update affected documentation and milestone/architecture
records; include related documentation in implementation commits when practical.
Never mark tasks or milestones complete while acceptance criteria are unverified.


## Dependency Policy

Do not introduce a new tool, framework, runtime, or major dependency merely for convenience.

Before adding one, determine whether the existing stack can reasonably solve the problem.

A new dependency should provide meaningful value in:

- reproducibility;
- reliability;
- maintainability;
- security;
- operational simplicity.

Pin important controller and tool dependencies when reproducibility benefits from it.


## Decision Making

For small implementation decisions, make a reasonable choice and proceed.

For significant architectural changes, stop and explain the proposed change before implementing it.

Ask before:

- introducing a new major technology;
- changing ownership between Terraform, Ansible, and Compose;
- changing the secret-management architecture;
- restructuring large portions of the repository;
- making destructive infrastructure changes;
- changing networking architecture.

Do not ask for confirmation for every minor implementation detail.


## Working Style

When given a task:

1. inspect the relevant repository files;
2. understand the current state before editing;
3. explain the current state briefly;
4. identify the smallest coherent solution;
5. implement it using existing patterns;
6. validate it;
7. review the diff;
8. split the work into logical commits when appropriate;
9. summarize what changed and any remaining work.

Do not expand the scope unnecessarily.

If the requested work reveals unrelated technical debt, mention it separately instead of silently fixing it.


## Architecture Quality

Prefer architecture that is:

- easy to understand;
- easy to navigate;
- modular where useful;
- explicit;
- reproducible;
- testable;
- replaceable;
- unsurprising.

Avoid both extremes:

- giant monolithic files that mix unrelated concerns;
- excessive fragmentation where understanding one workflow requires opening many tiny files.

Optimize for a future engineer being able to understand the repository quickly.


## Definition of Done

A task is complete when:

- the requested behavior is implemented;
- the architecture remains coherent;
- secrets remain outside Git;
- relevant validations pass;
- the diff contains no unrelated changes;
- documentation is updated when necessary;
- commits are small, logical, and properly named;
- remaining limitations are explicitly identified.

## Trust Boundaries

Forgejo is the trusted operational Git and CI/CD control plane. GitHub mirrors
are outbound publication or upstream surfaces by default; inbound
synchronization into privileged Forgejo repositories requires explicit review.
External repositories, forks, and upstream changes are untrusted until
intentionally adopted and reviewed.

Anyone who can modify code executed by a secret-bearing workflow must be
treated as capable of using those secrets. Validation and build workflows must
not receive infrastructure credentials, and privileged deployment workflows
must use trusted triggers, protected contexts, and least-privilege access.

## Repository-Scoped Infisical Bootstrap

Each Forgejo repository owns its own `INFISICAL_CLIENT_ID` and
`INFISICAL_CLIENT_SECRET` as Forgejo Actions repository secrets. These are only
bootstrap credentials for that repository's Machine Identity. Workload and
infrastructure secrets remain in the intended Infisical project and must not
be duplicated into unrelated repositories or centralized in a shared runner
identity.

Non-secret Infisical metadata such as project ID, environment, domain, and
secret paths belongs in versioned configuration or Forgejo Actions variables.
Universal Auth must produce short-lived runtime access without relying on a
human login or local credential cache.

Classify secrets separately as CI bootstrap credentials, application/workload
secrets, runner infrastructure credentials, or registration/bootstrap-only
credentials. Do not collapse these categories into one storage pattern.

`.infisical.json` is the tracked, non-secret source of truth for the
Homelab-IaC project/workspace identifier. Make, Ansible, and Terraform-related
workflows should derive that identifier from this metadata where practical;
never place client credentials in the file. Local operators and Forgejo CI use
the same `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET` names, supplied by
the local runtime shell or repository Actions Secrets respectively.

## Adoption And Legacy State

For existing manually-created infrastructure and services, use:

    DISCOVER -> CLASSIFY -> MODEL -> IMPORT/ADOPT -> CHECK -> REVIEW -> CONVERGE -> CLEAN LEGACY STATE LAST

Never replace working live state merely to make the repository cleaner. The
Forgejo runner connection credentials are runner infrastructure secrets owned
by the Homelab-IaC Infisical project. The legacy runner env mounts remain
compatibility state until the external CEM and theme workflows are migrated
and verified; do not remove or rotate them during repository validation.

Adoption preserves service contracts, not accidental implementation details.
Existing manually-built infrastructure may be intentionally modernized or
replaced when the declarative target is cleaner, provided dependent workloads
are preserved and migration is controlled.

When downtime is acceptable and backups exist, a clean replacement may be
preferable to continued adoption of historical implementation details.
Terraform resources intended for reconstruction must not inherit import-only
lifecycle workarounds. Workload bootstrap credentials belong to each
repository's CI workflow, while runner infrastructure credentials belong to
the Homelab-IaC Infisical project. Preserve workload behavior, not historical
runner identity.

## Registry

Forgejo's OCI registry should store real repository-owned build artifacts,
preferably under immutable commit-SHA tags. Do not create placeholder images or
populate the registry merely for appearance. The local `cem-ci:latest` image
is a future migration candidate, not an artifact to publish automatically.

## Project Navigation and Milestone Discipline

`docs/README.md` is the documentation index. `docs/architecture.md` describes
the current architectural direction and explicitly distinguishes verified
implementation from target design. `docs/roadmap.md` records milestone
dependencies. `tasks/README.md` defines the task workflow; `tasks/*.md` scopes
individual jobs. The documents in `docs/audits/2026-09-24/` are historical
evidence from the audited `fd4435e` baseline, not guaranteed live status.

Before implementation, inspect Git status and read the assigned task and
relevant architecture/roadmap/runbook material. Work on ONE explicitly assigned
task. Do not proceed to a subsequent milestone merely because the first task
was completed. If no task is assigned, report status and identify the next
eligible task without performing changes.

Task labels such as READY or IN_PROGRESS are planning metadata, not permission
for live modification. Explicit task-specific authorization is still required
for applies, infrastructure convergence, imports, migrations, credential
changes, production access, and destructive recovery tests. If evidence or
prerequisites conflict with a task, stop and report the discrepancy.

## Independent Bootstrap and State Authority

Normal CI/CD is NOT a bootstrap prerequisite. A trusted replacement controller
must be able to retrieve the externally available code and encrypted recovery
material, then restore the minimal control plane when Forgejo, Infisical, the
runner, and the remote backend are initially unavailable. Bootstrap and normal
deployment should reuse infrastructure modules and Ansible roles, not duplicate
implementations.

Every real resource has one declared IaC owner, and every Terraform root has
one writable authoritative state. Encrypted cloud recovery copies are sealed,
dated backups; file synchronization is NOT a live Terraform backend. Do not
auto-import, auto-adopt, auto-destroy, or choose replacement hardware from
resource discovery alone. Never migrate the bootstrap state's authority into
the service that it is needed to recreate.

GitHub contains an externally recoverable CODE copy, not a guarantee that
unpushed Forgejo/local commits are available. Verify the actual publication
state during recovery preparation. Hardware profiles belong in environment
configuration; generic components should accept placement, storage, network,
and explicit hardware requirements as inputs. Terraform and Ansible cannot
recreate unknown mutable application state without a declared provisioning
contract or a verified recovery artifact.

## Near-Term CI Quality Gate

The immediate implementation sequence is the CT301 runner trust/health
preflight followed by validation-only CI on authorized refs. CT301 uses a
rootful Podman socket: do not treat a job as safe merely because it receives
no secrets. Do not allow untrusted pull-request code to access that socket,
host resources, privileged connections, or production state.

Validation jobs must run without production Proxmox credentials, Infisical
runtime credentials, or live Terraform backend access. Use explicit offline
Terraform validation with the backend disabled and providers verified, Ansible
syntax checks, YAML and script tests, and existing runner/backup test suites.
Do not call Make targets that automatically inject production secrets from
an ordinary quality job; do not run production plans or applies in this CI.
Protected CD is a later, separately approved milestone requiring a qualified
backend, a reviewed state migration, narrow identities, and an independently
recoverable control plane.

## AGENTS.md Policy

`AGENTS.md` is versioned, public-safe project guidance and MUST be tracked in
this repository. Treat changes to it like code: review the diff, keep instructions
consistent with `docs/architecture.md`, `docs/roadmap.md`, and assigned tasks,
and validate before committing. Do not include operator-specific credentials,
private keys, secret values, recovery materials, or private local configuration.
Keep sensitive operator-only guidance in separately ignored local files.

Do not edit unrelated repositories or push to any remote without explicit
operator authorization. A task's READY status does not authorize a live change.
