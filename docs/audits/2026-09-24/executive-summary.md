# Architecture audit: executive summary

Audit date: 2026-09-24. Baseline: `fd4435e`. Documentation only; no infrastructure
changes, state migrations, commits or pushes. Evidence labels and detailed scope
are in [current-state](current-state.md).

## Assessment

The repository contains useful, working declarative components, but does not yet
demonstrate reconstruction of the whole homelab from an independent controller.
Do not equate guest adoption, a successful deployment, or a PBS snapshot with
complete disaster recovery.

- **VERIFIED IN SOURCE CODE:** seven Terraform roots, no child modules, nine
  Ansible roles, thirteen playbooks. Six stacks retain local state. CI is
  validation-only, intentionally without production state or provider credentials.
- **VERIFIED ON LIVE INFRASTRUCTURE:** four Proxmox nodes online; runner,
  Garage and PostgreSQL services active; Forgejo/Infisical HTTPS reachable;
  monitoring readiness endpoints respond; AdGuard and Caddy services active.
- **MISSING:** independently verified recovery copies of local Terraform states
  and private bootstrap inputs. Losing the operator controller remains a material
  control-plane recovery risk even while PBS protects selected guests.
- **VERIFIED IN SOURCE CODE:** normal Terraform wrappers depend on Infisical.
  No complete supported bootstrap path independent of Infisical/Forgejo exists.
- **REPORTED BY PREVIOUS QUALIFICATION:** PostgreSQL passed disposable CRUD,
  real lock contention/crash recovery/isolation and logical restore over SSH.
  **VERIFIED ON LIVE INFRASTRUCTURE:** production hostname-verified TLS remains
  incomplete: loopback listener and default certificate. No winner is selected
  between PostgreSQL and the as-yet-undeployed Consul candidate.
- **VERIFIED IN SOURCE CODE:** workstation roots adopt hardware without an OS
  clone source. Important foundations and mutable application identities remain
  outside IaC. Proxmox portability is currently limited by literal environment
  settings and hardware-specific mappings.
- **UNKNOWN / ACCESS BLOCKED:** monitoring SSH host key differs from known trust;
  no bypass performed. TrueNAS/PBS physical recovery dependencies and Infisical
  identity permissions are unverified. Runtime Universal Auth credentials absent.

## Preserve and improve

Preserve separated state roots, pinned provider/controller components, current
Terraform/Ansible/Compose ownership, independent CT bootstrap, least-privilege
direction and validation-only CI. Preserve the rejected Garage locking result;
do not migrate state there or replace native locking with a workaround.

Recommend **Option B**: incremental improvement inside the existing monorepo.
First protect authoritative state and prove recovery; then extract one repeated
CT concept and test a second profile. Do not split repositories or invent a
scheduler/orchestrator before interfaces and independent bootstrap are proven.

## First narrowly scoped milestone

Create a reviewed **state ownership and Recovery Kit v1 contract**: identify the
one authoritative copy of each root, classify the retired runner state, verify
external code publication, list required private inputs/identity recovery, select
encrypted offsite storage and independent key recovery, and specify a no-write
restore verification procedure. No backend migration or live changes in that
milestone. Actual export/upload/decryption drills require separate authorization.

Next: protect/test the kit; establish independent controller entry points;
finish candidate qualifications and select a backend; perform isolated recovery
and only then an approved canary and protected CI/CD. Stable module extraction
and hardware portability proceed in small, tested steps, not a rewrite.

## Documents

- [Current state and validation](current-state.md)
- [Dependency graphs and nine recovery cases](dependency-and-bootstrap.md)
- [Modularity, portability and options](modularity-and-portability.md)
- [State ownership, security and Recovery Kit](state-and-recovery.md)
- [Dependency-ordered milestones](milestone-roadmap.md)

Two existing commits are ahead of Forgejo origin; GitHub mirror freshness is
unverified. This audit adds six uncommitted documents. AGENTS.md stays untouched,
local-only and untracked. No existing Terraform state was migrated.
