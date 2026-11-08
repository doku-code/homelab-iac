# 160 - Windmill CE in a dedicated LXC

Status: BLOCKED before live provisioning. [Runbook and inputs](../docs/windmill.md).
Local source and static checks are distinct from successful deployment.

- [x] Shared-host rollback audit: no Windmill container/project/image/volume
  created, no credential/DNS/proxy mutation, no shared resources removed.
- [x] Dedicated pve-core root, new local state, strict guest targeting, Compose
  and persistent PostgreSQL; smoke/automation inventory prepared.
- [x] CTID210 checked free cluster-wide with no listed PBS snapshots; initial
  DHCP approved. No address claimed before reading the actual guest lease.
- [ ] Operator Universal Auth, reviewed isolated one-create plan, then dedicated
  CT creation and recording of the live assigned IP.
- [ ] Docker inside the unprivileged CT; secure admin; UI/API, real SQL query,
  completed job on the default worker; independent backup/restore status.
- [ ] Verify intended private access. Do not advertise an unverified DNS/proxy
  route or expose through the existing Cloudflare tunnel.

No changes to the old runner, other applications or existing states authorized.

Offline evidence: locked provider init with backend disabled, Terraform fmt and
validate, one mock-provider DHCP CT test, three synthetic guard/Compose/worker
proof tests, static Compose config, shell and Ansible syntax passed. The real
plan command stopped at missing controller Universal Auth; no plan, apply,
live Windmill job or runtime credentials were produced. Use `make windmill-plan`
from the authenticated operator shell. This is not a physical allocation or
live success claim.
