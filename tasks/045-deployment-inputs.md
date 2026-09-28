# 045 - Explicit reusable deployment inputs

- Status: IMPLEMENTED / locally validated; exact pushed-SHA CI remains a delivery gate.
- Dependencies: reconciled architecture; no full040, backend or live K3s gate.
- Initial scope: repository-only, first Stage A contract; no live deployment.

Use [input inventory](../docs/deployment-inputs.md). Add the smallest explicit
Infisical/private input selector feeding the SAME root and existing approval
guards. No fallback, new secret store, universal schema or parallel stack.
Expose the headless module public-key input at the selected root without changing
existing deployments. Evaluate one small private entry file only if needed;
native tfvars and Ansible inputs remain authoritative. Do not modify active state.

Acceptance: documented required/optional inputs and external prerequisites;
synthetic private/Infisical delivery gives equivalent non-secret configuration;
missing/ambiguous source fails closed; no secrets in logs/argv/test artifacts;
existing operator workflow unchanged; offline tests and exact-SHA CI pass.
Starter examples contain only documentation values and do not require original
operator identities. Recovery refuses missing authority/data, never empty fallback.
Follow-up separate scoped adapters for runner/monitoring, not all at once.
Live plan/application or secret access requires separate approval.

## Repository implementation - 2026-09-27

- Mandatory STAGE_A_INPUT_SOURCE=infisical|private, no default/fallback. Same root,
  native tfvars, provider token and saved-plan/hash/allocation/apply guards.
- Existing Universal Auth identity/project/CLI injection preserved. Pinned SDK
  login and environment token avoid secret argv; other stacks are untouched.
- Root ssh_public_key accepts own public key; null preserves deployed default.
  No new schema, backend, state, key or live operation.
- Synthetic Make tests cover source equivalence, missing/invalid credentials,
  unavailable source, failed auth/read/export, no ambient-token fallback/leaks,
  missing approval, hash mismatch and failed-plan cleanup/failed-apply retention.
- Mocked Terraform verifies default/custom key, invalid key/endpoint and existing
  allocation/hardware/lifecycle contracts. Stage A Ansible interfaces unchanged.
- Starter instructions are executable entry guidance, not a complete kit or
  recovery implementation. Missing existing state remains an incident, not a
  fresh-deployment fallback. Recovery authority validation remains040/050.

Completion evidence: local checks and exact-SHA Forgejo/GitHub result in delivery
report; no live equivalence or deployment is claimed. Next scoped input follow-up:
portable synthetic-controller qualification in050; runner/monitoring adapters
need separate tasks.110 incident and150 inventory remain independent.
