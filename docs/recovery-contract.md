# Recovery contract and Recovery Kit v1

Status: **SPECIFICATION; operator custody decisions and recovery tests pending**.
Owner: operator. Task [030](../tasks/030-state-recovery-contract.md) owns this
contract; [040](../tasks/040-recovery-kit-v1.md) produces/tests a kit and
[050](../tasks/050-independent-controller.md) implements independent controller
entry points. This document authorizes no export, restore or infrastructure write.

## Evidence and scope

2026-09-24 repository inspection: Makefile, Terraform roots, structural local
state metadata (no attributes/lineages/credentials printed), ignore rules,
controller dependencies, runner defaults and monitoring volumes. The only
configured remote is Forgejo origin. No external repository, private credential
store or live infrastructure was inspected. Exact private identities belong in
the encrypted manifest, never this document.

**Verified/source** means code or local file structure, not recoverability.
**Verified/reported** means dated qualification evidence or operator confirmation,
not a new test. **Unverified** means no sufficient recovery proof; **Missing**
means no implementation/evidence found here; **Decision** needs operator input.
Configured backup coverage does not imply freshness, encryption or restoration.
The [audit inventory](audits/2026-09-24/current-state.md),
[state evidence](audits/2026-09-24/state-and-recovery.md) and
[bootstrap analysis](audits/2026-09-24/dependency-and-bootstrap.md) remain historical.

The quality pipeline passed run139 on CT301/Linux AMD64 at 01ccefb, confirmed
by the operator. This proves repository checks, not recovery or runner isolation.
Tasks010/020 security acceptance is unchanged. No production backend is chosen;
PostgreSQL and Consul remain candidates, Garage is rejected for Terraform state.

## Authoritative sources and recovery dependencies

| Component / authority | Current backup or independent copy | Recovery prerequisites | Status / next proof |
| --- | --- | --- | --- |
| Public IaC: reviewed Git commit, HCL, Ansible, Compose, locks and non-secret metadata | Operator-reported GitHub copy; only Forgejo origin configured locally | Exact approved SHA available without Forgejo; verified tools and dependencies | Source verified; GitHub URL, refs, freshness and independent clone unverified. Record them privately/publicly as appropriate in 040-A |
| Terraform: per-root local state plus reviewed inputs; table below | Adjacent .backup on four roots only; not off-controller backups | Freeze writers, select exact root/lineage/serial, independent provider authorization and trust | Local structure verified; encrypted offsite capture and restore missing |
| Infisical: service DB plus matching application encryption material, config, projects, policies, identities and secret versions | Audit reports VM207 included in PBS; no compatible service export/restore proof | Recover DB/application versions and decryption material without Infisical; independent administrator access | Service recovery missing; backup completeness, ACLs and key custody unverified. Universal Auth credentials alone cannot reconstruct the secret service |
| Forgejo: DB, repositories, app config/keys, permissions, Actions secrets, registrations and package metadata/blobs | Audit locates upstream on TrueNAS; dataset/app layout and independent backups unknown | Restore a consistent set with its keys and storage access; independent Forgejo administrator recovery | Unverified; no server root/role or full restore evidence here |
| CT301 runner: Git OS/config model plus matching Forgejo registrations and Infisical connection/registry credentials | CT301 absent from audited PBS job; other coverage unknown | Independent controller; recovered Forgejo/Infisical or explicitly approved emergency injection; no duplicate active runner identity | Model verified; complete recovery unverified. Stop clone before production connectivity; re-registration is a separate approved alternative |
| OCI artifacts: ci-base:1.0.0 and cem-ci:1.0.3 from runner defaults | Live-use evidence, not independent artifact preservation; tags are mutable | Record actual digests/platform manifests and independently restore blobs, or qualify controller rebuild from pinned sources/dependencies | Recovery missing. ci-base source is here; CEM source is outside authorized scope. No dependency on a functioning runner to build its first image |
| Proxmox: installed host/cluster networking, storage, ACLs, trust, mappings and technical config | No complete host recovery set found; Git manages only selected guests/host settings | Compatible hardware/install media, console/local admin, network/storage inventory; review cluster identities before restore | Partial source verified; foundation recovery missing. Terraform guest roots do not install the first hypervisor |
| TrueNAS: system config, pools/datasets, shares/ACLs, app storage and applicable encryption keys | Independent copy/layout not established | Storage hardware/media, unlock material and local admin; identify where Forgejo and PBS actually store data | Unverified; preserve data and keys, not just exported settings |
| PBS: datastore bytes, config/access/trust and any encryption recovery material | Audit reports job coverage and CT300 snapshot; physical/offsite independence unverified | Restore PBS host/access first without relying on its own only backup; retain independently reachable required datastore bytes | Reported snapshot exists, full restore missing. crypt-mode=none observed historically; no claim of encrypted at-rest protection |
| PostgreSQL candidate: local bootstrap state; service DBs/roles/config and future TLS material | Logical sets at /var/backups/tfstate; code retains 7 days; dated PBS snapshot; see backup runbook | Compatible PG17, reviewed roles/ownership and independently available complete backup set | Disposable logical restore verified/reported, not production state recovery or bare-cluster restore. No production Terraform state stored there |
| Applications: owning DB/volume, not Terraform guest shape | Per-service independent backup inventory incomplete | Consistent database/files/identity set, versions, ownership and decryption keys | Missing complete inventory. Garage meta/data/layout/RPC identity; monitoring prometheus-data/grafana-data/alertmanager-data; Wiki/Vaultwarden and other services require owner-specific records |
| Workstations / personal data: installed OS and user datasets | PBS/other disk/data coverage not established here | Bootable images or verified OS/data backups; licenses, storage/hardware mappings as required | Hardware adoption verified in source; OS reconstruction and personal-data recovery unverified. Never declare these disposable because HCL exists |
| DNS/network/PKI: router/VLAN/routes, AdGuard rewrites, Caddy config, CA/trust and DNS-provider account | Audit observations, not independent configuration/key copies | Trusted address map, time, SSH fingerprints/CA roots, independent registrar/DNS/ACME and tunnel account recovery | Unverified. Reissue leaf certificates only after proving account/DNS/CA recovery; no TLS/SSH bypass as a bootstrap method |
| Pre-secret-manager access: approved break-glass accounts/SSH and decryption custody | iCloud Keychain plus offline path planned; storage/account recovery untested | Offsite account and MFA recovery without primary device or internal mail/SSO/Vaultwarden; separate offline decryption method | Decision/missing: custodian, recipients, offline method and tested access. Public admin key is not a substitute for private-key custody |

Large application and personal datasets are not recreated by Terraform/Ansible.
The small kit carries their recovery catalogue, not every payload. A pointer is
insufficient if the referenced bytes disappear with the homelab. Any essential
control-plane payload must have an independently retrievable protected copy;
otherwise full-loss recovery stays BLOCKED, even if the controller kit passes.
Do not invent retention, RPO/RTO, or guarantees for unknown backup arrangements.

## One state authority per root

All paths below are under terraform/stacks; active state is the operator's
root-local terraform.tfstate. Source and presence were rechecked; live ownership
was not reconciled. Resource identity must be confirmed privately before use.

| Root | Intended authority / recovery classification | Backend | Adjacent backup |
| --- | --- | --- | --- |
| deb13-monitoring | VM208 + image resource; 2 managed instances | Implicit local | Present |
| pve-lab-workstations | Five adopted workstation VMs; OS/data separate | Implicit local | Present |
| pve-compute-forgejo-runner-migration | Active runner CT301; 1 instance | Implicit local | Present |
| pve-compute-forgejo-runner | Historical retired runner only; recovery evidence, NOT an active writer | Implicit local | Absent |
| pve-core-garage | CT209 bootstrap; not a Terraform backend | Explicit local | Present |
| pve-core-tfstate | PostgreSQL CT300 bootstrap; must remain independent of itself | Explicit local | Absent |

Each of these six state files exists, is ignored, and has lineage/serial fields.
Private tfvars are present for monitoring, workstations and both runner roots;
Garage/tfstate also need runtime inputs (including public SSH-key inputs).
terraform/examples/cloud-image-vm has private tfvars but no local state: example,
not an authoritative deployment. Absence must not authorize creating resources.
No Terraform environment overrides were present during inspection; other
controllers/writers and outside copies remain unverified.

Contract: freeze every writer before capture or recovery; operator attests the
writer inventory. Privately record root, backend/workspace/path, resource identity,
lineage, serial, SHA256, capture time and source commit. Preserve the historical
runner state distinctly, never use its CT300 ID for PostgreSQL, never delete,
merge, re-import or move it as cleanup. Existing historical Make targets are not
recovery entry points. Local file locks do not serialize independent controllers.

Restore copies first to a disconnected read-only recovery workspace. If identity,
generation or freshness cannot be established, STOP; no automatic empty-state
fallback or choosing the highest serial across different lineages. Recovery
requires explicit designation of one writer and one authoritative location;
fence old writers before hand-back. Offsite generations stay immutable recovery
copies, not synchronized active state. Preserve bootstrap-root independence in
any later backend decision; no backend is migrated in 030/040.

## Recovery order and cycle escape

1. Outside the homelab: trusted replacement controller, out-of-band instructions,
   approved Git SHA/code bundle, offsite access, independently held decryption
   method. Retrieve and verify the kit without internal DNS, Forgejo, Infisical,
   PBS or state backend. Do not require CI or the failed Mac's keychain session.
2. In isolation: decrypt, verify manifests/files, select state generations,
   reconstruct tools and inspect prerequisites without live provider operations.
   Missing items fail closed. Freeze/fence surviving writers before any future
   recovery connection; loss of contact is not proof a writer is stopped.
3. Separately approved foundation recovery: network/console, first Proxmox host,
   local storage, TrueNAS and PBS where required. Preserve data; recover their
   credentials/config from independent custody, not from a guest they must host.
   Supply bootstrap address/trust mapping and time before normal DNS/PKI returns.
4. Restore DNS/PKI and required consistent control-plane payloads. Infisical DB
   and matching encryption keys come from pre-outage copies; Forgejo DB/repos/
   registry likewise. Their order follows actual storage dependencies, not a CI
   job. If the only copy is on unavailable PBS/storage, recover that layer first;
   if lost with no independent copy, STOP rather than reinstalling away data.
5. Restore any later-selected backend using separately held host state, data,
   roles and trust, never its own inaccessible backend. Currently all real stack
   states stay local; neither PG nor Consul is a prerequisite to start recovery.
6. Recreate CT301 with the existing roles from the controller, initially stopped.
   Restore coherent registrations/auth and verified OCI artifacts before jobs.
   Use approved controller publication/rebuild or preserved artifacts, not the
   runner-to-registry bootstrap cycle. Test in an isolated allocation later.
7. Validate identity, application recovery and (if selected) backend locking;
   explicitly hand back one state writer and normal Infisical delivery. Only
   then re-enable authorized jobs. Actual restore, deployment and DR proofs
   belong to separately authorized drills, not this specification or CI139.

Normal Make Terraform wrappers call Universal Auth and require healthy Infisical.
They are NOT the independent recovery interface. Task050 must add a narrow,
reviewed path using the same roots/roles with temporary secure recovery inputs,
without process-argument secrets or a new everyday secret store. This path is
currently missing; a manifest alone cannot remove that implementation blocker.

## Minimum kit and private manifest

Generation name: recovery-kit-v1-<UTC timestamp>-<Git short SHA>, never overwrite
an earlier generation. This is a specification, not a directory created here.
Use an approved private staging location outside the checkout, restrictive
permissions, encryption before transfer and no sensitive logs. If a future
implementation stages inside this repository, verify ignores first: arbitrary
JSON/dumps/archives are NOT covered merely by state ignore patterns.

| Manifest section | Minimum contents / rules |
| --- | --- |
| Header | schema version, generation ID, UTC capture/completion, approved Git SHA, operator/custodian, freeze evidence, per-component status; incomplete is not successful |
| Code | independent URL + exact ref/SHA and verified Git bundle at that SHA including required history; public source/lockfiles/runbook only; no blanket checkout archive |
| Files | relative path, component ID, bytes, SHA256, classification, producer/version/time, capture consistency boundary; reject symlinks/path traversal/unexpected files on extraction |
| States | six exact state copies with root/backend/workspace, lineage/serial, resource identity, original authority and recovery-only marker; historical runner explicitly quarantined; original .backup generations labeled separately, never substituted silently |
| Inputs/access | reviewed private tfvars and missing runtime inputs; approved long-lived recovery access, SSH/CA trust and necessary private identities; key fingerprints/references, expiry/revalidation requirements; do not scrape all operator files |
| Control plane | consistent Infisical and Forgejo DB/config/key recovery sets, or checksummed independently downloadable protected payload references; matching versions and restore prerequisites; runner identity pairing, registry manifests/blobs/digests |
| Foundations/data catalogue | Proxmox/TrueNAS/PBS/DNS/PKI/network config and recovery access; per-application owner, authoritative data, independent backup ID/location, encryption-key ID, dependencies, freshness and last restore evidence; unknowns explicit |
| Tools/artifacts | platform, version, source, checksum/signature trust, dependency locks; externally available verified downloads or cached necessary installers/providers/wheels/collections/images. Declare internet requirement; no claim of air-gapped bootstrap without complete tested cache |
| Evidence | independent retrieval/decryption/integrity results, tested controller, missing items, test date and limits; next freshness review and responsible operator |

Encrypt the whole private manifest and payload: states, inputs, keys, dumps,
role hashes, registrations and access catalogue are sensitive. Public code and
this specification need no secrecy; any outer receipt must be minimal (opaque
generation ID, ciphertext size/hash, encryption format/version, no private
inventory). SHA256 detects corruption, not trusted provenance by itself: retain
the expected receipt via independently trusted custody and use authenticated
encryption. Select format/recipient verification in 040, not a new product here.

Keep OUT: sole decryption key/recovery factors, plaintext exports in cloud/Git,
live state synchronization, plans, process caches, .venv, transient access tokens,
job logs, indiscriminate workstation archives and bulk personal data. Keep the
last proven recoverable generation; age/count retention and freshness thresholds
are operator decisions, not inferred from the PG seven-day local policy.

Capture consistency matters: code SHA plus input/state generation together;
service DB, keys and blobs from a documented compatible boundary. Per-file
checksums cannot make inconsistent application snapshots restorable. Record
change-driven recapture needs after state/identity/config updates; refuse to
label a stale or incomplete set current. No capture schedule is changed here.

The ciphertext destination and account recovery must be outside failed internal
services. iCloud Keychain is the planned convenience custody path, not the only
key copy. A separately protected offline key/recovery path and account/MFA
recovery must work without the original device, internal SSO/mail or Vaultwarden.
An independently stored encrypted offline generation should cover cloud outage;
its media/location and custodian need approval. Never store the sole decryption
method inside the archive or behind the same sole account/device failure.

## Qualification boundary

Task040 proves one independently retrieved/decrypted generation, exact state/
input inventory and fresh-controller tool/static checks while internal services
are unreachable. A test-only export is not full-control-plane recoverability:
every required referenced payload must also be retrievable or remain BLOCKED.
Task050 then implements/proves the emergency interface and authorized read-only
trust checks. Full isolated service/data restore follows under 080-B. The
specific decisions and pass/fail gates are maintained in [040](../tasks/040-recovery-kit-v1.md),
not duplicated across runbooks. No restore time or recovery-point guarantee
exists until measured in the relevant drill.
