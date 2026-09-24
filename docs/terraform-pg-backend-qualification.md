# PostgreSQL backend qualification

## Status: disposable qualification passed, not production migration approval

The later [production-candidate checkpoint](terraform-pg-production-gates.md)
records live DNS/TLS blockers and measured idle usage. It does not extend the
SSH-forwarded results below to the final native TLS endpoint.

On 2026-09-24 the operator reported the isolated host apply completed with
1 added, 0 changed, 0 destroyed. Read-only checks confirmed CT300 on pve-core,
hostname `tfstate`, `192.168.0.30/24`, gateway `192.168.0.1`, DNS `192.168.0.20`,
search `home.arpa`. The Terraform bootstrap root is
`terraform/stacks/pve-core-tfstate`, with explicit LOCAL backend and one CT
resource. No existing Terraform state was migrated or backend changed.
CT301 remains the active runner and was not modified.

## Deployment and host health

`make tfstate-configure` uses the repository controller and dedicated inventory,
playbook and `tfstate` role. Debian repositories supplied PostgreSQL server and
client **17.11-0+deb13u1**, after an explicit fresh APT metadata refresh. No
alternate package repository, Docker, nesting or production database is needed.

- Live convergence: 12 OK, 6 changed, 0 unreachable, 0 failed.
- Subsequent check/diff: 9 OK, 1 changed (APT metadata refresh), 2 read-only
  commands skipped by check mode, 0 failures, no configuration diff.
- `postgresql@17-main` active, cluster online, automatic startup enabled.
- Data: `/var/lib/postgresql/17/main` on the 16 GiB local-lvm root disk.
- Configuration: `/etc/postgresql/17/main`, including `conf.d/tfstate.conf`.
- Log: `/var/log/postgresql/postgresql-17-main.log`.
- fsync, full_page_writes and synchronous_commit are all ON; 128 MiB shared
  buffers and 30 connections. Authentication configuration has zero parse errors.

`dev-mqueue.mount`, `run-lock.mount`, and `tmp.mount` report mount conflicts,
not permission-denied failures. `/tmp` and `/run/lock` are writable mode 1777;
`/dev/shm` is tmpfs. APT, PostgreSQL initialization, service operation, and all
database tests worked. No mount units, Proxmox configuration or LXC features
were changed. These degraded systemd units remain a documented LXC artifact.

The reused IP still had the retired runner's SSH host key in the controller's
global known_hosts. The replacement ED25519 key was independently verified
via trusted pve-core `pct exec 300`, then used through an ignored, task-local
known_hosts file. Strict host checking remained enabled; global SSH trust was
not rewritten. Operators must verify the replacement key before updating
their own trust file, not disable host verification.

## Transport and least privilege

For this disposable milestone PostgreSQL listens ONLY on `127.0.0.1:5432`.
Two independent controller Terraform processes connect through an authenticated,
host-key-verified SSH forward. Database authentication is SCRAM-SHA-256 with
random temporary passwords; plaintext PostgreSQL traffic stays on loopback
inside the encrypted SSH transport. This is NOT a native verify-full TLS test,
a direct LAN connection test, or a Forgejo job test.

Ansible allows peer administration for local postgres and loopback SCRAM only
for members of the temporary `tfstate_qualification` group; all other access
is rejected. The group and all its login roles are absent after qualification.
No credentials are provisioned on the runner or written to Infisical.

The harness gives each independent root its own disposable database. The
setup owner initializes the schema with the actual Terraform binary, then
becomes NOLOGIN. Runtime A/B logins have CONNECT, schema USAGE, table DML and
sequence USAGE/SELECT, without ownership, CREATE, superuser, replication or
role-management privileges. PUBLIC database access is revoked. The second
database has its own runtime login; cross-database CONNECT is denied.

Implementation correction to the design: Terraform **1.16.1** creates
`public.global_states_id_seq`. State-schema-only sequence grants failed on
the initial synthetic write, before lock qualification. The final recipe
also grants public schema USAGE and USAGE/SELECT on that exact sequence,
not schema CREATE or blanket ownership. Failed disposable attempts were
cleaned up; no existing state was involved.

## Reproducible qualification and observed evidence

`make tfstate-qualify` runs `scripts/qualify-pg-backend.py` with exactly
Terraform 1.16.1 and only the built-in `terraform_data` resource. It creates
fresh client directories beneath ignored `tmp/` and unique disposable
databases/logins. It refuses an existing qualification group. It never loads
an existing root, uses `-lock=false`, or calls force-unlock.

With a separately verified host-key file:

```sh
make tfstate-qualify TFSTATE_KNOWN_HOSTS=tmp/tfstate-known-hosts
```

The ordinary default is the operator's `~/.ssh/known_hosts`.
`GUEST_SSH_PRIVATE_KEY_FILE` can select the existing authorized SSH key.
Passwords are supplied through process environment for Terraform and SSH stdin
for SQL provisioning, never backend HCL, command arguments or saved plans.
The harness checks generated files for password bytes and absence of a local
authoritative `terraform.tfstate`; it removes temporary artifacts in finally.

Actual successful run:

| Gate | Evidence |
| --- | --- |
| State initialization/read/update | A wrote; B read independently and updated; serial increased, lineage unchanged |
| Same-state exclusion | A held a real apply at a bounded provisioner barrier; granted advisory lock observed in pg_locks; B exited 1 with state-lock error; state unchanged |
| Waiting client | B remained pending and state unchanged during A's hold; after A released normally B applied successfully; no locks remained |
| Cross-root isolation | Separate-database apply succeeded while A still held its lock; distinct lineage and denied cross-database CONNECT |
| Client crash | A was SIGKILLed with its process group while holding the lock; its database sessions disappeared in 0.31 seconds; waiting B then completed |
| Final consistency | Output `recovered`, one synthetic resource, serial 5, original lineage; Terraform plan exited 0 (no changes) |
| Logical recovery | pg_dump custom-format stream restored into a third isolated database; complete stored state matched; Terraform initialized, read the output and produced a no-change plan |
| Cleanup | All three disposable databases, four roles and qualification group removed; temporary directories removed; no password found in generated files |

The dump was streamed through memory/SSH without a persistent dump file.
The isolated restore reused the disposable role definitions within the same
cluster: it does not prove bare-cluster role reconstruction or full disaster
recovery. These tests prove two independent clients on one controller, not
yet operator-versus-Forgejo execution. A silent network blackhole, server
restart, simultaneous first initialization and full PBS CT restore were not
tested. A crashed apply can leave partially completed infrastructure; the
native lock release does not roll an apply back. Only synthetic resources
were used here. Never substitute forced unlocking for session diagnosis.

## PBS coverage and historical CT300 ambiguity

PBS job `backup-94190086-c727` now includes
`200,207,202,206,204,209,300`. Only 300 was appended. Full before/after job
comparison verified every other field unchanged: `3:00`, storage `pbs`,
snapshot mode, enabled, `keep-all=1`. No backup job was triggered and no old
recovery point was removed or retention changed.

Existing `pbs:backup/ct/300` snapshots predate the PostgreSQL deployment:

- `2026-09-13T07:00:03Z`
- `2026-09-18T07:00:12Z`
- `2026-09-19T07:00:00Z`
- `2026-09-20T07:00:03Z`
- `2026-09-21T07:00:05Z`
- `2026-09-22T07:00:05Z`

These belong to the retired runner allocation, not PostgreSQL. The reused
numeric group will also contain new tfstate snapshots. Inspect timestamp and
backed-up guest configuration/hostname before any restore; never restore an
old runner snapshot over PostgreSQL merely because its VMID matches. The
first new scheduled backup and a full CT restore drill remain unverified.
PBS inclusion is coverage configuration, not proof of a completed backup.

## Production gates and recovery procedure

No production databases, canary migration or Forgejo automation were created.
Before any separately authorized migration:

1. Approve issuer, renewal and deployment ownership for PostgreSQL native TLS
   with SAN `tfstate.doku-lab.net`; verify clients use `sslmode=verify-full` and
   a trusted CA. The intended endpoint is `tfstate.doku-lab.net:5432`. DNS and
   certificates are not configured here; no AdGuard/Caddy changes were made.
   Do not proxy PostgreSQL as HTTP or expose it publicly.
2. After TLS is ready, deliberately enable the LAN listener and restrict
   hostssl SCRAM rules per database/role to confirmed operator and protected
   CI source addresses. Qualify that actual transport and both client contexts.
3. Provision one database per root and distinct least-privilege operator/CI
   logins, injecting secrets through existing Infisical Universal Auth at
   runtime. Keep backend credentials separate from Proxmox credentials;
   ordinary CI validation jobs receive neither. No production secrets exist yet.
4. Automate and monitor private logical dumps plus protected role metadata
   before PBS, with reviewed retention and encrypted off-host recovery. The
   test stream is not a scheduled logical-backup implementation. Verify the
   first new PBS snapshot and restore to a separately allocated isolated CT.
5. For recovery, isolate the original authority, provision compatible PG17,
   restore least-privilege roles and an isolated database, then restore the
   custom dump. Compare full state, lineage, serial, addresses and outputs;
   initialize disposable clients and repeat lock exclusion/crash tests before
   a reviewed cutover. Never allow two writable backend authorities.

The single pve-core host/root disk remains an availability dependency. Daily
PBS scheduling is not a demonstrated RPO or RTO; 24h/2h design targets remain
unverified. There is no HA, WAL/PITR qualification, failure alerting integration
or measured silent-network-loss lock-release bound. The bootstrap Terraform
state stays LOCAL and needs protected off-host recovery independent of this
PostgreSQL instance. Existing Terraform states remain exactly where they were.
