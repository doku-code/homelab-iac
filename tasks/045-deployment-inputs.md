# 045 - Explicit reusable deployment inputs

- Status: PLANNED; metadata contract documented, adapter not implemented.
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
Live plan/application or secret access requires separate approval. Not DONE from
this specification. Next smallest code step: Stage A selector + public-key input.
