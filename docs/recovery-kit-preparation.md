# Recovery Kit v1 preparation

Current sequencing is in the [reconstruction roadmap](roadmap.md): portable050
synthetic preparation can precede real040 capture;035 VM is optional, and no
full production kit is required for disposable K3s learning. The capture gates
and prior observations below remain valid; the earlier mandatory VM-first order
does not. Future K3s states/snapshot/token inventory needs an explicit schema
update before capture, not silently accepting an incomplete six-root kit.

2026-09-25: repository preparation, NOT a produced or recovered kit.
The [accepted contract](recovery-contract.md) remains authoritative for scope;
[040](../tasks/040-recovery-kit-v1.md) owns approval and qualification gates.
No backend choice, state migration, production export or key handling occurred.

## Approved custody and independent code

Public source: <https://github.com/doku-code/homelab-iac>, main. Independently
queried before this work: `0ccbccb20d563020ddcbdbcdb7270c2cf6f4be92`.
Recheck the exact final reviewed SHA after every push and at capture time;
availability today does not prove future freshness. Preserve a verified Git
bundle containing that exact commit and required history as an additional
artifact, not another active repository/state writer. A later capture must run
`git bundle verify` and prove an isolated clone checks out the approved SHA.
No bundle was captured in this preparation.

iCloud Drive is approved for **ciphertext generations only**, never active
state. Existing Apple account recovery and a spare signed-in iPhone are
operator-confirmed; neither independent retrieval nor offline key recovery has
been tested. Do not expand this into an Apple account redesign.

Use a private unsynced local directory, proposed
`~/.local/share/homelab-recovery/staging/<generation>`, mode 0700 and umask 077.
Resolve its real path and verify it is outside every synced/backup-to-cloud
plaintext location before approval. In particular this checkout is on Desktop:
do NOT stage private data here, in Documents, or under iCloud. Repository
`recovery-private/` and `*.age` ignores are defense in depth, not sync protection.
No staging directory has been created. Keep the full private manifest encrypted.

Use the established [age format and recipient mechanism](https://github.com/FiloSottile/age)
for authenticated encryption of the complete archive. Before implementation,
pin an available release for both controller platforms and verify upstream
release integrity (including its published Sigsum proof where available).
Do not invent crypto or install an unpinned script. The producer needs only a
verified public recipient; no private identity is needed to encrypt. Record
the recipient fingerprint through independent trusted custody, and keep the
private identity in the existing protected convenience custody plus a separate
operator-held offline method. Its sole copy must not be in the kit, Infisical,
the lost controller or the same sole cloud account. Offline media/custodian and
recipient are still operator decisions. No key is generated/read by this task.

Future capture encrypts locally before any copy to iCloud. Keep a minimal
independently trusted receipt: opaque generation ID, ciphertext bytes/SHA256,
age version and recipient fingerprint. Hashes are not producer authentication.
Do not overwrite the last proven generation. Decryption, wrong-key/tampering
tests, upload and independent retrieval require separate approval.

## Read-only inventory and targeted capture plan

Sources below are metadata observations, not permission to export. Any database
backup must use a version-compatible, consistent procedure, not blindly copy
live database files. Capture DB/config/keys/blob sets at one documented boundary.

| Component | Evidence on 2026-09-25 | Future targeted payload / unresolved gate |
| --- | --- | --- |
| Six Terraform authorities | Existing root-local state structure rechecked; addresses only, no attributes disclosed | Exact roots in contract; reviewed private inputs and runtime inputs; lineage/serial and writer attestations in private manifest. Historical runner remains recovery-only, NOT PostgreSQL CT300 |
| Proxmox / PBS | pve-core job enabled, schedule 3:00, includes 200,207,202,206,204,209,300; PBS at .15, backup-store | Host/cluster config, trust, storage/mappings and independent admin custody; datastore bytes and keys separately recoverable. No schedule or retention changes |
| PBS snapshots | Metadata lists 207:7, 208:5, 300:6, 209:2; no 301. Other historical guest snapshots also exist | Counts prove neither freshness nor restore. Old/new CT300 identity must be reconciled by snapshot date/config before use. CT301 missing here; other coverage unknown |
| TrueNAS / Forgejo | Proxmox NFS pve_library points to .13:/mnt/pve-pool/pve_library; existing root SSH denied | TrueNAS system config, dataset/share/ACL map and unlock custody; Forgejo consistent DB/repos/config/keys/Actions/package blobs. Actual app/dataset paths and offsite copies UNVERIFIED; NFS export alone does not locate Forgejo |
| Infisical | VM207 in backup job and snapshot inventory; existing debian SSH denied; Universal Auth client pair unavailable in this execution environment | Matching DB, application encryption material, version/config and policies/identities; no values accessed. Read-only identity cannot be presumed able to export recovery keys or service DB |
| DNS/trust | Presence only: CT200 /opt/AdGuardHome/AdGuardHome.yaml; CT204 /etc/caddy/Caddyfile | Review targeted DNS/network/trust config, independent account/CA/SSH custody; associated credential paths require private review. File presence is not an independent backup |
| OCI | CT301 local image metadata confirms tags/digests below | Preserve registry manifests/blobs independently or qualify pinned-source rebuild outside the failed runner. Cache is not offsite recovery; CEM repository not inspected |
| Technical application data | Contract inventory identifies remaining service-specific DB/volume gaps | Catalogue each DB/files version pair, ownership/UID/GID/ACLs, dataset/mount paths, permissions, encryption keys and restore ordering. Bulk personal bytes excluded, recovery/reattachment references required |

Observed local RepoDigests (not remote availability or backup verification):

- `git.doku-lab.net/doku-code/ci-base@sha256:c09d2765dfb9927efaffddbc746a3aaa1272c29763d7f420a375296f9a4c9b16` for `ci-base:1.0.0`.
- `git.doku-lab.net/cem/cem-ci@sha256:9925857f7ce94919c51b87a918a0e888cd13b807dc8d100e4bd827f17f0e5c9a` for `cem-ci:1.0.3`.

No new credential is required for synthetic validation. Next inventory requires
the operator to make the **existing** read-only Universal Auth identity available
through the normal runtime variables, and approve a metadata-only TrueNAS/
Forgejo service-layout inspection through existing administrative access. Do
not create or elevate an identity. If existing access cannot support this,
STOP and specify the precise read-only capability and proposed Homelab-IaC
Infisical path before requesting a new credential; none is provisioned here.

## Capture consistency procedure (not executed)

1. Review the exact source SHA and six state roots in the contract. Enumerate
   operator shells, scheduled jobs and CI writers; current Make is an operator
   writer, not evidence that no other writer exists. Get a private freeze
   acknowledgement from every writer; network unreachability is not fencing.
2. While frozen, capture each exact local authority with its private inputs,
   original path, backend/workspace, lineage/serial and resource identity.
   Compare pre/post hashes and serials; any change invalidates the generation.
   Label original adjacent backups separately, never silently promote them.
3. Record historical runner quarantine and PostgreSQL CT300 distinction.
   New pve-lab-controller has no state/allocation; do not invent a seventh
   capture. If later deployed, revise contract/schema inventory deliberately.
4. Capture only reviewed technical payloads under service-specific consistency
   boundaries and record version, time, dependencies, independent location,
   encryption custody and last restore evidence. Missing required bytes or
   merely local PBS references block completeness.
5. Seal manifest/hashes, validate structure, encrypt, obtain approved independent
   receipt and only then release the freeze. Originals remain the sole writable
   authorities; kit states are inert recovery-only copies, never initialized.

## Private manifest schema v1 and verifier

The deliberately small structural schema below is enforced by
`scripts/verify-recovery-kit.py` using Python's standard library. It is not an
exporter or a claim of full contract compliance. Unknown fields, duplicate keys,
missing/extra files, symlinks, traversal and mismatched metadata fail closed.

| Field | Required type / meaning |
| --- | --- |
| schema_version | Integer 1 |
| generation | 1-120 ASCII letters/digits/underscore/hyphen; unique capture identifier |
| git_commit | Exact 40-character lowercase hex SHA, also supplied independently to verifier |
| files | Nonempty array; each entry has path, bytes (nonnegative integer), sha256 (64 lowercase hex), kind |
| path | Unique normalized relative POSIX file path inside isolated directory; not manifest.json |
| kind | state, code, catalogue or payload; at least code and catalogue required |
| state-only fields | root (one of all six contract roots), lineage (nonempty string), serial (nonnegative integer), recovery_only=true |

Each state path must be `states/<root>.tfstate`; six distinct roots required.
Its JSON version must be 4 and lineage/serial must equal the manifest. The
private reviewed catalogue carries the richer contract fields: custodians,
timestamps, versions, freeze proof, backend/workspace, authority, sensitive
inputs, dependencies and independent payload receipts. The verifier checks its
bytes, **not semantic completeness**. Likewise code bytes are checked, not Git
bundle semantics. Those require separate manual/operational qualification gates.
Root identity cannot be derived from a state file alone: verify lineage against
the trusted capture inventory, not an attacker-supplied manifest. Authenticated
decryption and trusted expected SHA/receipt must precede use.

After separately approved decryption into isolated storage:

```sh
python3 scripts/verify-recovery-kit.py /approved/unsynced/generation --expected-commit <reviewed-full-SHA>
```

Output is PASS/FAIL only; no paths, state attributes or secret values are logged.
The tool assumes a quiescent trusted local directory (not hostile concurrent
writes); it does not safely extract archives or authenticate the producer.
CI runs `make recovery-check` with synthetic temporary data only. Tests include
success, absent/corrupt files, wrong lineage/root/commit, traversal, links,
duplicates and unexpected files. Synthetic code.bundle is intentionally not a
real Git bundle: passing the structural check is not recovery qualification.

## Freshness proposal and next approvals

Proposal, NOT approved RPO/RTO or a configured schedule: recapture after any
state/input/identity/trust/service-config change, review freshness weekly, keep
the last three verified generations plus three monthly checkpoints **if measured
size permits**. Keep the last proven generation until a replacement is recovered.
Database change rates and artifact sizes are unknown; measure before approving
component ages, offsite capacity and retention. PostgreSQL's local seven-day
policy is not the kit retention policy.

Next operator actions are deliberately separate:

- Assign [050 portable synthetic testing](../tasks/050-independent-controller.md)
  on independent Mac/Linux first; no production kit is needed for that phase.
  The [035 VM procedure](headless-controller.md) is an optional adapter only.
  Its allocation, plan, creation/start and convergence require separate approval;
  the preserved preflight does not authorize deployment.
- Complete blocked metadata inventory, approve recipient/offline custody and
  unsynced staging realpath. Then approve an exact per-component capture list,
  writer freeze and local encryption; production payload export is not yet
  authorized. Upload and retrieval/decryption drill require their own approval.

The later drill must block internal services/DNS, fetch GitHub or the bundle,
retrieve/decrypt independently, verify the manifest and rebuild the controller
for eight backend-disabled readonly root validations and static checks. No
provider plans or restored states become active. A VM hosted on pve-lab proves
controller replacement, **not recovery from loss of pve-lab**. Full control-plane
restore and backend selection remain later work. Task050's portable emergency
entry points are a parallel implementation track, not dependent on this VM.
