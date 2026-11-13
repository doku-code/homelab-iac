# PostgreSQL logical backups and external protection

Implemented and verified on CT300 on 2026-09-24. No existing Terraform state
was migrated. This completes the scheduled logical-backup mechanism, not full
production security or full guest recovery qualification.

## Ownership and schedule

The `tfstate` Ansible role installs `/usr/local/sbin/tfstate-logical-backup`,
`tfstate-logical-backup.service` and `tfstate-logical-backup.timer`.
The enabled timer runs at **02:00 America/Toronto**, explicitly matching the
timezone of pve-core's existing **03:00 PBS** job. Persistent scheduling
catches missed runs after boot. The timer itself has not yet reached its next
scheduled firing; the same service was started manually and verified twice.

The service runs as root, uses local postgres peer administration, and creates
custom-format dumps of every connectable non-template database, plus globals
(including role password hashes). No database password is needed for backup.
Each database dump is transactionally consistent; this is not a cross-database
snapshot transaction. There are no production state databases yet.

Backup sets live in `/var/backups/tfstate/<UTC timestamp>/`, mode 0700, files
0600. `manifest.json` maps database names to OID-named dump files, avoiding
database names in filesystem paths. `globals.sql` and dumps are sensitive
recovery artifacts. Do not cat, commit or upload them to public storage.

An exclusive lock prevents overlap. Only successfully completed sets become
`latest`, using an atomic symlink replacement. Archive table-of-contents
validation is a preliminary check, not a restore proof. Incomplete sets are
removed on handled errors; the previous complete set remains intact. Local
retention is **7 days**, applied only to timestamped complete sets after a
successful new backup. Unrelated directories/symlinks are never pruned.
The newest complete backup is always retained.

Errors produce a nonzero service result and a sanitized journald message;
systemd exposes the failed unit. A 45-minute service timeout bounds execution.
Inspection commands on CT300:

```sh
systemctl list-timers tfstate-logical-backup.timer
systemctl show tfstate-logical-backup.service -p Result -p ExecMainStatus
journalctl -u tfstate-logical-backup.service --since today
```

No monitoring or external alert receiver was changed. Off-host failure alerts
and automated stale-backup detection remain a production gate. A failed dump
could leave PBS capturing an older complete set; inclusion alone does not
prove freshness. A timeout/SIGKILL can leave an `.incomplete-*` directory:
inspect it locally before removal; it is never advertised as a complete set.

## Actual qualification

`make tfstate-backup-qualify TFSTATE_KNOWN_HOSTS=tmp/tfstate-known-hosts`
uses independently verified SSH trust and disposable databases/roles. It
runs the existing real Terraform locking/crash/isolation test, starts the
actual backup service, restores its dump into an isolated database, compares
the entire state, and requires a no-change Terraform plan after restoration.

Observed: state CRUD, lock exclusion, waiting-client release, isolation and
restore all PASS. Killed-client session disappearance was 0.17 seconds in
this run; final synthetic serial 5, one resource, output `recovered`.
All test databases and live roles were removed. The private retained backup
set contains synthetic test data and revoked test-role hashes; this is not
an active credential cache. It follows the explicit local/PBS retention.
Tests still used SSH forwarding, NOT the final native verify-full endpoint.

Initial Ansible deployment: 16 OK, 5 changed, zero failures. A follow-up
streaming improvement avoids loading whole dumps into memory during archive
inspection. The updated service was deployed and ran with Result=success,
ExecMainStatus=0. Unit validation passed. Offline tests cover permissions,
retention scope, failed-run cleanup and preservation of the previous set.

## External copy and PBS limits

A CT300-only snapshot backup succeeded in 15 seconds:
`pbs:backup/ct/300/2026-09-24T15:02:50Z`, notes identifying PostgreSQL tfstate
and distinguishing the retired runner. The root filesystem, including logical
dump sets, was included. Storage `pbs` points to `192.168.0.15`, datastore
`backup-store`, outside CT300. Upload completed and the snapshot is listed.
No full guest restore was performed.

The existing job remains `200,207,202,206,204,209,300`, schedule `3:00`,
storage `pbs`, `keep-all=1`. This one-off backup disabled pruning. All six
September 13-22 historical runner recovery points remain. Local seven-day
retention does NOT prune PBS snapshots or remove archived role hashes there.

Important: the existing PBS client uses **crypt-mode=none**. We did not change
its encryption policy, identities or permissions. The copy uses the existing
authenticated PBS infrastructure, but client-side encryption is absent and
datastore at-rest encryption/access policy has not been qualified. Do not
claim encrypted recovery protection or broader physical fault isolation.

## Restoration procedure and remaining approval

For an approved isolated target, obtain the selected complete set from PBS
or the private local directory. Inspect its manifest without logging secret
contents. Recreate necessary roles/ownership under local administrative
access, then restore the selected custom archive using `pg_restore` with
`--exit-on-error` into a NEW database. Never blindly replay globals into a
running production instance: review role/password ownership and revoke any
obsolete qualification roles. Compare full state, lineage, serial and outputs,
then initialize disposable Terraform clients and repeat lock tests before
any approved cutover. The implemented harness demonstrates same-cluster
isolated logical recovery, not bare-cluster globals reconstruction.

A full PBS guest restore needs explicit temporary VMID/storage approval and
disconnected or isolated networking. Never overwrite CT300 or start a clone
with its .30 address on the production bridge. Do not select a pre-deployment
runner snapshot. This full restore, an actual scheduled firing, off-host
alerting, encryption review and RPO/RTO measurement remain unproven.

The CT300 Terraform root remains LOCAL. PBS contains guest data, not the
Mac's local Terraform bootstrap state. An independently protected, versioned
and encrypted recovery copy of that state still needs a destination/access
decision; never create a second active authoritative copy.
