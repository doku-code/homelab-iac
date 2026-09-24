# State ownership, security and recovery

Evidence labels: [current-state](current-state.md). No state/backend modifications.

## State inventory

**VERIFIED IN SOURCE CODE / LOCAL FILE STRUCTURE:** all six stack roots have
`terraform.tfstate` beside their HCL. No configured remote backend, workspace
selector or workspace-state directory was found. No TF_DATA_DIR, TF_WORKSPACE
or TF_CLI_ARGS override is present in this audit environment. Counts below were
obtained structurally without outputting resource attributes or credentials.

Paths are relative to the repository; every state listed is ignored by Git.

| Root | Backend | Managed instances | Adjacent .backup | Ownership |
| --- | --- | --- | --- | --- |
| terraform/stacks/deb13-monitoring | Implicit local | 2 | Yes | VM208 and cloud-image download |
| terraform/stacks/pve-lab-workstations | Implicit local | 5 | Yes | Workstation VMs501/502/503/601/602 |
| terraform/stacks/pve-compute-forgejo-runner-migration | Implicit local | 1 | Yes | Active CT301 |
| terraform/stacks/pve-compute-forgejo-runner | Implicit local | 1 | No | Historical runner, not current CT300 PostgreSQL |
| terraform/stacks/pve-core-garage | Explicit local | 1 | Yes | CT209 |
| terraform/stacks/pve-core-tfstate | Explicit local | 1 | No | CT300 PostgreSQL bootstrap |
| terraform/examples/cloud-image-vm | Implicit local | No local state found | No | Example; no evidence of active ownership here |

Recorded state Terraform version is 1.16.1. Private tfvars exist for the example,
monitoring, workstations and both runner roots; PG/Garage use tracked inputs and
runtime public-key/provider inputs. Presence is not proof of backup completeness.
Cached backend metadata for PG/Garage identifies local with no custom state path;
other roots lack cached backend metadata, consistent with their implicit local source.

Adjacent `.backup` files are not independent/offsite recovery. **UNKNOWN:** copies
outside authorized scope. **MISSING:** verified off-controller inventory/restore
evidence. PBS protects guests, not the controller's local Terraform files.

The old runner root rejects VMID300 in variables.tf:17. Live CT300 is now tfstate
on pve-core, not the retired pve-compute runner. This is a historical state/ID
ambiguity, not proof that both roots currently manage the same live object.
Old command/inventory references still need a separately reviewed retirement
boundary. Do not delete/re-import/merge states to make the inventory look clean.

All states remain local: local file locking does not serialize independent Mac
and CI copies. A fresh CI checkout with empty state must never plan production
as if it owned current resources. Future backend use needs identity/lineage
verification and must fail closed if the expected state is missing.

## PostgreSQL, Garage and Consul evidence

**VERIFIED ON LIVE INFRASTRUCTURE:** CT300 runs PostgreSQL 17.11; data at
`/var/lib/postgresql/17/main`; listen_addresses=127.0.0.1; ssl=on, default
snakeoil certificate SAN tfstate.home.arpa, not intended tfstate.doku-lab.net.
Internal final name resolves to .30 from controller, CT300 and CT301. Backup
timer enabled; service reports Result=success and ExecMainStatus=0. Three
historically diagnosed LXC mount-unit failures remain; no changes made.

**VERIFIED IN SOURCE CODE:** native PG17, local peer administration, loopback
qualification-group SCRAM and reject other clients. No production database/login
provisioning, production TLS issuance or autonomous renewal delivery implemented.
Native verified TLS, stable approved source addresses, per-root operator/CI
credentials and Infisical production injection remain unfinished.

**REPORTED BY PREVIOUS QUALIFICATION:** real Terraform CRUD, lock exclusion,
waiting-client continuation, killed-session release, cross-database root isolation,
logical restore and no-change plan passed over SSH forwarding. Latest backup
qualification recorded session release in 0.17 seconds; this is neither a
network-partition bound nor a new audit measurement. No final TLS endpoint test,
bare-cluster globals reconstruction or full PBS restore has passed.

**VERIFIED ON LIVE INFRASTRUCTURE:** PBS include list
`200,207,202,206,204,209,300`, schedule 3:00, keep-all=1. CT301 and VM208 are
not in that observed job; other external backup arrangements are UNKNOWN.
Seven CT300 snapshots listed: six September13-22 historical runner snapshots and
one PostgreSQL snapshot dated September24. Never select by CTID alone.
**REPORTED BY PREVIOUS QUALIFICATION:** PostgreSQL snapshot uploaded successfully;
client crypt-mode=none, datastore at-rest protection unqualified. Full restore,
scheduled firing observation and off-host backup failure alerts remain unproven.

**VERIFIED IN SOURCE CODE:** backup service dumps databases plus globals, atomically
publishes a complete set under `/var/backups/tfstate`, restricts modes, serializes
runs and retains seven days locally. Dumps/globals include sensitive state and
role hashes. Separate database dumps are not one cross-database transaction.

**REPORTED BY PREVIOUS QUALIFICATION:** Garage2.4.1 allowed a second real client
to modify locked state twice; rejected for authoritative Terraform backend.
Do not rerun or work around that result here. **MISSING:** any deployed/qualified
Consul candidate. Backend comparison remains a future controlled evaluation,
not a PG selection in this audit.

## Public repository security

**VERIFIED IN SOURCE CODE:** ignore rules cover state, plans, private tfvars,
environment files, keys, tmp and .venv. No tracked files in those state/plan/tfvars
categories or private-key markers were found. This limited scan is not a claim
that every historical commit is secret-free. AGENTS.md remains untracked;
never stage broad untracked content as part of this audit.

Infisical project metadata is non-secret and canonical. Universal Auth uses
runtime credentials; runner login/read tasks are no_log and explicitly run in
check mode. Actual identity ACLs and secret-path visibility are **UNKNOWN /
ACCESS BLOCKED** because runtime client credentials are absent, not proven denied.

Important source risks:

- Makefile:22,24 supplies client secret and access token as process arguments.
  Suppressed command echo is not protection from same-host process inspection.
- Common wrapper exports project/environment secrets without explicit narrow
  path selection. Effective identity scope was not verified.
- Runner configuration/registry auth is mode0600 and no_log. Rootful Podman
  socket access is root-equivalent within the runner CT. Global valid_volumes
  permits its socket; a comment saying publication-only is not per-connection
  enforcement. Ordinary validation does not request/automount it, but review
  who may change any workflow allowed onto this shared daemon.
- CI uses versioned image/action tags rather than immutable digests/SHAs.
  Compose/standalone Python are checksummed; Terraform zip lacks checksum;
  ci-base uses mutable Node base and unpinned Infisical setup/package, and its
  gitleaks archive lacks a pinned checksum. Gitleaks is not run by validation.
- Generated plans/state are sensitive even with Terraform sensitive flags.
  Keep them out of public logs/artifacts; local permissions/lifetimes need a
  deliberate policy, not only `.gitignore`.
- TLS private keys and recovery artifacts were not read. No dedicated current
  Recovery Kit path/policy exists; arbitrary .sql/.dump/.json exports would not
  all be ignored. Agree a private location and verify ignore rules before export.

## Minimal Recovery Kit v1

Everything in this section is **PROPOSED ONLY**. Do not create/upload the kit
as part of this audit. It contains encrypted recovery copies, never active state.

| Material | Preserve exactly or regenerate | Producer / prerequisites |
| --- | --- | --- |
| Local states for six stacks, historical state separately labeled | Exact lineage/content with generation manifest; never mix old/new CT300 | Trusted controller; no concurrent Terraform writer during capture |
| Private root inputs and required non-public host settings | Preserve reviewed values; public allocations already in Git | Controller and authorized operator |
| Git commit, lockfiles, tool/artifact versions/digests | Re-fetch verified artifacts or independently archive essentials | External Git plus verified release access/cache |
| Proxmox/PBS/NAS administrative recovery access and trust | Preserve enough to regain access; rotate later under approval | Independent accounts/key access, not Infisical alone |
| Infisical backup and application decryption material | Preserve exact compatible snapshot/key set | Healthy secret service/storage or verified PBS recovery artifact |
| Forgejo configuration/DB/registry recovery references | Preserve mutually consistent metadata/blobs/keys; kit may reference separately protected backups | Forgejo/storage/PBS and independent restore access |
| Runner identities and necessary registry access recovery | Preserve paired registrations, or deliberate re-registration with Forgejo admin | Infisical/Forgejo recovery; never credentials in public docs |
| Selected backend recovery data, roles/trust | Add after selection; independently recoverable bootstrap host state always retained | Backend backup service + trusted export/restore process |
| DNS/PKI technical configuration | Preserve required trust/identity; leaf cert reissuance only with tested DNS/CA access | DNS/Caddy/config exports and independent DNS-provider access |

Do not indiscriminately copy every application/user dataset into this kit.
Store small essential material plus checksummed manifests/references to larger
independent recovery sets. Image caches, .venv and transient access tokens are
regenerable. Existing encrypted application data is not recoverable with newly
invented encryption keys. Avoid preserving revocable short-lived tokens as if
they were durable bootstrap credentials.

Manifest: UTC capture time, source Git commit, root/backend classification,
private lineage/serial/checksum, versions, backup IDs, required key identifiers,
dependencies and operator custody. Manifest itself belongs encrypted when it
contains sensitive operational detail; public docs describe the format only.

Choose an external cloud destination for encrypted snapshots. iCloud Keychain
holds the decryption key per operator direction, but also arrange a separately
protected offline recovery key/path and cloud-account recovery independent of
lost devices. Never put key and ciphertext under the same sole failure path.
File sync is transport for sealed copies, not a live Terraform backend.

Automation can later package, checksum, encrypt and verify uploads from the
controller; service backup exports depend on those services being healthy.
Capture before outage, version generations, retain known decryptable copies,
and alert on stale/incomplete exports. No export automation exists today.

Acceptance: recover ciphertext on a different trusted machine, decrypt without
the normal Mac/control plane, verify every manifest checksum/reference and tool
version, inspect structural state identity privately, and document missing
inputs without provider writes. Actual guest restore is a later approved drill.

Prevent two active states: seal/read-protect recovery generations; label them
recovery-only; freeze all writers before selecting one generation; restore into
an isolated workspace first; explicitly designate the authoritative writer and
backend on hand-back. Never allow a stale local fallback to keep applying after
remote recovery. Capture measured RPO/RTO rather than claiming HA from backups.
