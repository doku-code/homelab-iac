# Dedicated PostgreSQL Terraform backend proposal

Status: DESIGN ONLY, 2026-09-23. No PostgreSQL service, identity, secret,
backend block or state migration has been created. Deployment needs separate
approval after workstation recovery and design review.

## Decision and scope

Garage remains general internal S3 storage and is permanently rejected by
this evaluation as authoritative Terraform state storage. PostgreSQL would
own BOTH state and locking; there is no split Garage-state/PostgreSQL-lock
design. Documentation is not qualification: the disposable tests below are
mandatory before any canary migration can be separately approved.

Terraform documents PostgreSQL 10+ support, environment-based credentials,
workspace-keyed state tables and native advisory locking. `force-unlock` is
not supported; session failure releases locks. Connection loss detection
is not necessarily immediate. See the [native pg backend documentation](https://developer.hashicorp.com/terraform/language/backend/pg).

## Live discovery and allocation gate

Read-only pve-core discovery found 16 logical CPUs, about 30.6 GiB total RAM,
16.3 GiB available RAM, and 383 GiB available local-lvm capacity. This is a
point-in-time capacity check, not a resource reservation or performance test.
No Infisical application/database contents were inspected or reused.

Live cluster VMIDs: 200, 201, 202, 203, 204, 206, 207, 208, 209, 301, 400,
401, 501, 502, 503, 601, 602, 8100, 8101, 8200, 9001, 9101, 9102, 9103.
For example, 210 was absent, but is NOT selected or reserved. Retired IDs
are not presumed reusable. No IPv4 is allocated; absent DNS/ping responses
would not establish freedom from a reservation. STOP at this allocation gate.
The operator must assign an authoritative free VMID and static IP, followed
by a fresh inventory/conflict check before any future apply.

## Proposed service

- Dedicated unprivileged Debian 13 LXC on pve-core, without nesting or Docker.
- 1 vCPU, 2 GiB RAM, 512 MiB swap, 16 GiB local-lvm root disk initially.
- Native systemd PostgreSQL 17, with packages `postgresql-17` and
  `postgresql-client-17` from Debian; no alternate APT repository.
- Debian 13's observed candidate is `17.11-0+deb13u1`, confirmed by a read-only
  APT query on the existing Debian 13 guest. No package was installed.
- Declare major 17; record exact installed package versions at deployment
  and apply reviewed security updates, rather than pinning an obsolete patch
  indefinitely. PostgreSQL 17 is supported through November 2029.
- Data under `/var/lib/postgresql/17/main`, configuration under
  `/etc/postgresql/17/main`; keep both on the backed-up root disk initially.
- Retain fsync/full-page writes and synchronous commit; no unsafe speed tuning.
  Start with 128 MiB shared buffers and 30 maximum connections; verify under
  the actual Mac/CI test workload before increasing concurrency.
- Independent Terraform bootstrap root with LOCAL authoritative state and
  an encrypted off-host recovery copy. Never host its own bootstrap state
  inside PostgreSQL. Garage's bootstrap state also stays local.

PostgreSQL 18 is the newer upstream major; 17 is the supported native Debian
choice that avoids an unnecessary repository/runtime change. Sources:
[Debian package](https://packages.debian.org/trixie/postgresql-17),
[upstream lifecycle](https://www.postgresql.org/support/versioning/).

## State separation and least privilege

Use one PostgreSQL instance dedicated only to Terraform. Choose **one database
per independent root**, not one shared default workspace table. Suggested
database names include `tf_pve_lab_workstations`, `tf_deb13_monitoring` and
`tf_pve_compute_runner`. These names do not authorize migration of those roots.
Retired resources require separate lifecycle decisions, not automatic migration.

Within each database, use schema `terraform_remote_state` and workspace
`default`. Do not use workspace names as a substitute for independently
secured roots. Keep an explicit root-to-database mapping in future non-secret
configuration. The operator and CI for a given root MUST use the same database
and workspace, or they will not contend on the same state.

Upstream's current pg client uses row IDs and a special creation-lock key,
not a schema-qualified key. Separate databases avoid unintended advisory-lock
overlap between roots and simplify per-root restore/access boundaries. This
is a design inference from [upstream source](https://github.com/hashicorp/terraform/blob/main/internal/backend/remote-state/pg/client.go),
not a claim that the moving main branch exactly matches installed 1.16.1.
Verify the selected Terraform release during implementation and test cross-root
independence as well as same-root exclusion.

Proposed permissions per database:

- A NOLOGIN owner role owns database/schema/table/index/sequence. Administrative
  provisioning runs locally via PostgreSQL peer authentication under Ansible.
- Separate LOGIN roles for operator and protected CI, both scoped to that
  root's database. No SUPERUSER, CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS.
- Revoke PUBLIC database CONNECT/TEMP and schema CREATE; grant only database
  CONNECT, schema USAGE, table SELECT/INSERT/UPDATE/DELETE and required sequence
  USAGE/SELECT. No runtime role owns schema objects or receives broad DDL rights.
- Bootstrap the backend's exact schema with the selected Terraform release
  under a temporary local setup role, then transfer ownership/revoke setup
  access. Runtime uses `skip_schema_creation`, `skip_table_creation`, and
  `skip_index_creation`; verify initialization under the restricted logins.
- A read-only plan credential is not assumed sufficient: Terraform may need
  writes/locking during backend initialization. Prove permissions experimentally.

No live SQL or permission changes are authorized now. Schema grants above are
a proposal to validate, not a tested permission recipe.

## Network and native TLS

Proposed hostname `tfstate-pg`; service DNS `tfstate.doku-lab.net`, internally
rewritten by AdGuard DIRECTLY to the new guest's operator-approved IP. Gateway
`192.168.0.1`, resolver `192.168.0.20`, LAN search domain `home.arpa`.
This is native PostgreSQL TCP/5432, **not HTTP behind Caddy reverse_proxy**.
No new proxy layer, public record, Cloudflare proxy, tunnel or port forward.

Use PostgreSQL native TLS with a SAN for `tfstate.doku-lab.net` and clients
configured with `PGSSLMODE=verify-full` and an explicit trusted CA bundle via
`PGSSLROOTCERT`. Prefer an existing operator-approved CA issuance path. None
has been established by this audit: selecting the issuer and renewal/deployment
ownership is an approval gate. Reusing Cloudflare DNS-01 is possible only with
a reviewed certificate-delivery mechanism; do not copy a shared wildcard key,
give the database Cloudflare credentials, or pretend the Caddy HTTP mechanism
already configures PostgreSQL TLS. No TLS deployment is proposed implicitly.
See [PostgreSQL certificate verification](https://www.postgresql.org/docs/17/libpq-ssl.html).

Restrict listening to localhost and the allocated LAN IP. Use hostssl rules
with SCRAM-SHA-256, per-database/per-role matching and exact client source
addresses. Allow the operator Mac's reserved address and the protected
Terraform job's actual egress address (CT301 is .31, but container NAT/source
must be verified). Deny other LAN clients and plaintext remote authentication.
Guest firewall and pg_hba rules require reviewed configuration, not broad
subnet trust. The Mac reservation/CI egress are still to be confirmed.
No PgBouncer/transaction pooling: preserve backend session-lock semantics.

## Infisical and workflow credentials

Proposed Homelab-IaC paths, with environment selected explicitly:

- `/terraform/backend/postgresql/<root>/operator/PGUSER`, `PGPASSWORD`.
- `/terraform/backend/postgresql/<root>/ci/PGUSER`, `PGPASSWORD`.

PGHOST, PGPORT, PGDATABASE, schema and TLS mode are non-secret reviewed metadata;
the CA certificate is public trust material, not a password. Existing Universal
Auth must retrieve only the intended per-root role's path at runtime. Proxmox
provider credentials remain separate paths/permissions from backend access.
Do not create an elevated shared identity. Existing repository identity policy
must be reviewed for narrow path access, with no new identity created here.

Use PGUSER/PGPASSWORD runtime variables; avoid credential-bearing connection
strings, command arguments, backend HCL, tfvars, saved plans and logs.
`PG_CONN_STR` is supported, but is not needed for the preferred split-variable
model. Clear inherited conflicting PG variables before setting reviewed values.
No shell tracing; no debug dumps of state or environment. Plans can contain
secrets even when passwords are provided via environment and must stay private.

Operator Mac and a future protected Forgejo Terraform workflow use distinct
logins with the same per-root backend identity. Ordinary validation workflows
receive none of these credentials. Runner daemon/host secret mounts are not
the delivery mechanism; use repository-scoped Actions bootstrap secrets and
short-lived Infisical access. No CI deployment workflow is implemented now.

## Mandatory disposable qualification

1. After separate deployment approval, create a disposable database and limited
   operator/CI test logins. Confirm TLS verification and cross-database denial.
2. Create two separate client working directories, one on the Mac and one in
   the protected CI execution context, both targeting the same disposable
   database/schema/default workspace. Use pinned Terraform and only built-in
   `terraform_data`; no Proxmox provider or existing state.
3. Initialize pg, write synthetic state, read it independently from B and SQL,
   update normally, compare output, serial and lineage without printing secrets.
4. Hold A in a bounded test provisioner after native lock acquisition. Observe
   its session/advisory lock in pg_locks using a separate audit/admin connection.
5. Launch B with `-lock-timeout=0s`: require a lock error, nonzero exit and
   unchanged state. Also test B waiting with a bounded lock timeout while A
   holds the lock; it must never enter its mutation barrier early.
6. Release A normally. Verify A's final state and disappearance of its lock;
   B must then acquire and update successfully.
7. Hold A again, kill that test client unexpectedly, and measure server session
   and lock disappearance. Verify B can proceed only after the session ends.
   No `force-unlock` workaround is available for pg.
8. Compare state lineage/serial/output to the last successful operation. A
   crashed apply may leave partial logical work, not automatically rolled-back
   infrastructure; use synthetic resources only. Verify a clean subsequent plan.
9. Test a dropped-network session separately with bounded keepalive detection;
   do not assume immediate release. Propose server TCP keepalive 30s idle,
   10s interval, 3 probes, subject to measured behavior and operator review.
   Do not enable session timeouts that can release a legitimate long apply lock.
10. Test simultaneous initialization of empty state, and independent databases
    concurrently, to catch initialization races and cross-root coupling.
11. Revoke disposable logins and remove only the disposable databases/artifacts.
    Any mutual-exclusion failure rejects the candidate, with no custom wrapper.

These tests have NOT been run. No documentation claim substitutes for them.

## Backup and recovery proposal

Add only the eventual new VMID to the existing relevant PBS job after approval;
preserve all other IDs, schedule, storage and retention. Do not assume automatic
inclusion. Propose daily consistent custom-format pg_dump per root database,
plus restricted globals/role metadata, scheduled before PBS captures the CT.
Treat dumps, role hashes and state as secrets: private permissions, encrypted
off-host backups, restricted restore access and explicit retention decisions.
Do not put them in Garage or Git. PBS captures the whole data/config disk but
snapshot coverage alone is not proof of database recovery.

Initial proposed RPO is 24 hours; proposed RTO is 2 hours, both unverified and
requiring operator acceptance. If this is insufficient, design WAL archival/
PITR separately rather than claim the daily scheme provides it. Alert on failed
dumps/PBS jobs and storage exhaustion. Single-node availability remains limited.

Restore drill: use a separately approved isolated target, no production DNS
switch, restore roles/schema/database, verify dump integrity and per-root
lineage/serial/resource addresses/outputs, initialize two clients against the
restored disposable database, and repeat locking/crash recovery. Test both
logical restore and PBS CT restore. Keep original backend isolated during a
disaster cutover to prevent split authority. Preserve encrypted original local
states before any future separately authorized migration.

## Required operator decisions

First restore workstation USB visibility and complete a real start/stop cycle.
Then approve/revise this design, allocate a free VMID/IP, confirm client source
addresses, choose TLS issuer/renewal ownership, approve per-root identity
permissions and RPO/RTO, and authorize ONLY disposable deployment/testing.
Production state migration remains a later independent approval.
