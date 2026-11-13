# Incremental milestone roadmap

Everything below is **PROPOSED ONLY** unless marked already completed.
Evidence baseline and limits: [current-state](current-state.md).
No milestone was executed or approved by this audit. Each should be a small
reviewable change, not one combined refactor/deployment/migration commit.

## M1: State ownership and recovery contract

- Objective: identify one authoritative state per root and define Recovery Kit v1.
- Prerequisites/dependencies: this audit and operator custody decisions; no other milestone.
- Done: six local states inventoried, bootstrap roots explicit, CT300 reuse guard.
- Missing/components: private generation manifest, historical runner classification,
  external GitHub freshness verification, private-input inventory, offsite/key
  recovery destination and access decisions.
- Deliverables: public ownership/runbook contract, private-manifest schema, agreed
  copy-versus-active-state policy; no secrets or exports in Git.
- Acceptance: every root has an owner/recovery source, old/new CT300 cannot be
  confused, required inputs and lost-device key recovery are accounted for.
- Risk: choosing the wrong state generation; preserve all originals.
- Production changes: none. Approval: contract review; export/upload not included.
- Suggested boundary: docs(recovery): define authoritative state and kit contract.

## M2: Produce and verify Recovery Kit v1

- Objective: survive loss of the controller without creating another writable state.
- Prerequisites/dependencies: M1; approved encryption/storage/custody and writer freeze.
- Done: ignore patterns and recoverable source/tool version information.
- Missing/components: minimal packaging, encryption, external transfer, manifest,
  independent key/account recovery and new-controller no-write verification.
- Deliverables: private encrypted dated recovery generation linked to Git commit,
  minimal repeatable exporter, public procedure and sanitized verification record.
- Acceptance: independent download/decryption/checksum and private state-identity
  checks succeed without normal Mac, Forgejo, Infisical or runner; no provider writes.
- Risk: secret export leakage, stale snapshots, lost decryption key, duplicate writer.
- Production changes: no infrastructure; sensitive data export occurs.
  Approval: explicit export/destination/key-custody authorization required.

## M3: Independent controller entry points

- Objective: reuse current Terraform/roles without depending on unavailable services.
- Prerequisites/dependencies: M1-M2; trusted Proxmox/SSH recovery access.
- Done: .venv setup, pinned CI Python, separate roots, runner OS bootstrap.
- Missing/components: tool/trust/state preflight, explicit recovery credential
  delivery without normal Infisical wrapper, safe bootstrap/reconcile distinction.
- Deliverables: small Make targets/runbooks and read-only doctor; no automatic
  import, adoption, resource reassignment or destruction.
- Acceptance: clean trusted controller can validate inputs/tools/state while
  Forgejo/Infisical are unavailable; bootstrap preconditions fail closed.
- Risk: accidental live command or bootstrap stopping an active runner.
- Production changes: none for implementation/offline tests; later drill separate.
  Approval: interface/security review; live execution separately approved.

## M4: Offline validation and narrow safety corrections

- Objective: catch known repository defects before production refactors.
- Prerequisites/dependencies: M1; can proceed alongside M2-M3.
- Done: runner synthetic tests, PG backup unit tests, three-root CI validation.
- Missing/components: six-stack validation policy, backup tests in CI, real secret
  scanning, checksum/pinning gaps, exporter-role responsibility, Make consistency.
- Deliverables: separate focused changes for each concern, same secretless CI.
  Investigate monitoring SSH trust and routing through trusted evidence before
  proposing any route edit; classify legacy runner entry points without state removal.
- Acceptance: all intended offline checks pass; expected exporter tasks contain
  no Compose deployment; dangerous targets remain explicit and review-bound.
- Risk: broad cleanup hiding behavioral changes; do not batch unrelated fixes.
- Production changes: none. Approval: normal code review; live reconciliation not included.

## M5: Foundational recovery inventory and runbooks

- Objective: close unknown mutable-state and physical dependency gaps.
- Prerequisites/dependencies: M1-M3; explicit read access to missing systems.
- Done: live cluster/storage inventory and proxy destinations, selected PBS metadata.
- Missing/components: TrueNAS/PBS fault domains, application backup consistency,
  Infisical encryption keys, Forgejo DB/packages/permissions, DNS/Caddy/tunnel
  technical state, independent access and backup coverage policy.
- Deliverables: private recovery manifest updates and public dependency/runbook
  contracts; narrow source-of-truth classification before service adoption.
- Acceptance: every foundational service has a verified backup/source, dependencies,
  restore inputs and isolated-test plan; independent kit covers essential keys.
- Risk: exporting too much, incomplete DB/blob/key sets, assumed backup independence.
- Production changes: no service changes for discovery; backup exports may be needed.
  Approval: scoped access/export separately authorized, no automatic broad cleanup.

## M6: Finish PostgreSQL candidate readiness

- Objective: qualify the actual production security/transport/recovery design.
- Prerequisites/dependencies: M2-M3; approved identity/TLS/source-address decisions.
- Done: native PG17, DNS, disposable SSH-forwarded CRUD/locking/isolation,
  logical restore, backup timer and listed PBS PostgreSQL snapshot.
- Missing/components: hostname-verified TLS issuance/renewal, scoped autonomous
  delivery, operator/CI identity model, stable egress restrictions, final-endpoint
  negative TLS and contention/crash tests, scheduled freshness/alerts, encryption
  policy and isolated bare-cluster/PBS recovery.
- Deliverables: focused security changes and sanitized final-endpoint qualification
  record; bootstrap state remains local; no production state migration.
- Acceptance: native verify-full, wrong-host/untrusted-chain rejection, real B
  exclusion while A holds lock, crash release, isolation and verified recovery.
- Risk: exposing DB or invalid renewal/overbroad credentials; current loopback
  containment preserved until gates pass.
- Production changes: yes, narrowly on backend and approved security dependencies.
  Approval: explicit credentials/certificate/network and restore allocation approval.

## M7: Isolated Consul candidate evaluation

- Objective: compare another self-hosted backend on equivalent acceptance criteria.
- Prerequisites/dependencies: M2-M3; independent allocation/resource/trust approval.
- Done: no Consul deployment or qualification exists.
- Missing/components: disposable candidate only, TLS/ACL/storage/backup design,
  actual Terraform locking/session failure/isolation and verified restore tests.
- Deliverables: separate experiment root, measured resource/operational costs,
  failure evidence and cleanup plan, no existing states or backend edits.
- Acceptance: same safety/recovery hard gates as PG; report topology tradeoffs,
  single-node limitations or additional quorum cost, not assumed HA.
- Risk: increasing control-plane complexity or unfair comparisons.
- Production changes: none to existing services; new isolated resources required.
  Approval: explicit experiment allocation/deployment/cleanup authorization.

## M8: Select backend and approve migration contract

- Objective: evidence-based PG/Consul decision, not a technology preference.
- Prerequisites/dependencies: M5-M7 and independently usable recovery material.
- Done: Garage rejection is settled; local state inventory complete.
- Missing/components: comparative decision record, root exclusions, state identity
  preflight, operator/CI permissions, backup RPO/RTO, writer-freeze/rollback policy.
- Deliverables: selected backend contract and one proposed low-risk canary.
- Acceptance: locking/security/restore hard gates pass, bootstrap roots do not
  depend on their own backend, cost/availability/maintenance limits accepted.
- Risk: choosing based on CRUD alone or accepting silent lock failure.
- Production changes: none in decision milestone. Approval: operator selection required.

## M9: Isolated independent control-plane and CT301 recovery drill

- Objective: prove bootstrap without the normal controller/control plane/runner.
- Prerequisites/dependencies: M2-M3, M5, candidate recovery procedures; M8 for
  final selected-backend hand-back. Begin smaller isolated service drills earlier.
- Done: runner clean bootstrap code and controller image publication escape path.
- Missing/components: restore foundation identities/data, verify registry artifacts,
  recreate runner from same code, recover selected backend, measure timing.
- Deliverables: isolated drill report and corrected runbooks/kit; no source-service
  shutdown required. Never let clones poll production with copied registrations.
- Acceptance: trusted new controller plus external code/kit/PBS material succeeds;
  no old Mac-only files, preexisting runner or hidden Infisical requirement.
- Risk: duplicate IPs, registrations, certificates or Terraform writers.
- Production changes: no intentional source mutations; isolated resources needed.
  Approval: explicit allocation/isolation/restore/cleanup and hand-back boundaries.

## M10: Canary state migration

- Objective: migrate exactly one approved non-bootstrap root without resource change.
- Prerequisites/dependencies: M8-M9, current sealed backups, trusted inputs and freeze.
- Done: none migrated; preserve this until approval.
- Missing/components: authoritative lineage check, destination absence verification,
  reversible migration procedure and independent read/lock checks.
- Deliverables: one-root migration record with no resource address/module refactor.
- Acceptance: matching state identity, no unintended create/change/destroy, restore
  rehearsal, one authoritative backend and no old local writable fallback.
- Risk: duplicate/empty/wrong state or credentials in plan logs.
- Production changes: authoritative state storage yes; guest resources no.
  Approval: explicit root-specific migration approval and reviewed plan required.

## M11: Protected Terraform/Ansible CI/CD

- Objective: first independently recoverable normal deployment workflow.
- Prerequisites/dependencies: M3-M4, M8-M10; trusted workflow governance and egress.
- Done: secretless validation, one functioning runner, repository-scoped auth model.
- Missing/components: protected trusted-ref plans, fixed root/host allowlists,
  short-lived credential delivery, authoritative-state preflight, sanitized logs,
  operator review of exact plan and least-privilege apply/Ansible controls.
- Deliverables: plan first; separate later opt-in apply/convergence workflow.
- Acceptance: untrusted PRs receive no production secrets/state; missing state
  fails closed; lock contention enforced; approvals bind intended ref/plan;
  runner loss recoverable independently. No broad rootful-socket trust assumption.
- Risk: secret-bearing arbitrary code, stale plans, privileged shared-runner jobs.
- Production changes: only explicitly approved workflow runs; implementation alone none.
  Approval: security/identity/trigger policy and each initial deployment required.

## M12: First reusable CT component

- Objective: extract one repeated CT concept, not every root into a framework.
- Prerequisites/dependencies: M1, M3-M4; keep separate from M10 migrations.
- Done: three similar clean CT roots; literal site inputs known.
- Missing/components: small explicit interface, environment profile, outputs,
  address-preserving extraction plan and documentation.
- Deliverables: one in-repo module plus tests; hardware workstations unchanged.
- Acceptance: synthetic configs validate; reviewed real-root plans show no resource
  replacement; lifecycle safety policy remains explicit.
- Risk: changed resource addresses/defaults causing recreation.
- Production changes: not for initial isolated module; adoption may alter state addresses.
  Approval: review extraction and any state-address operations separately.

## M13: Disposable second-environment profile

- Objective: prove portability with different node/storage/network/capacities.
- Prerequisites/dependencies: M12, M2-M3; approved independent allocations.
- Done: no existing second-profile evidence.
- Missing/components: explicit capability/preflight inputs, clean deploy/reconcile/
  recovery and bounded cleanup outside active guests.
- Deliverables: second profile and evidence, no hardcoded doku-lab dependency in module.
- Acceptance: no module edits between profiles, service minimums met, second
  convergence understood, recovery tested and cleanup explicitly reviewed.
- Risk: allocation collision, storage/network capability mismatch.
- Production changes: no active workload changes; disposable resource creation.
  Approval: explicit allocation/deploy/cleanup required.

## M14: Progressive adoption of foundational services

- Objective: make one existing service's configuration reproducible at a time.
- Prerequisites/dependencies: M5/M9, protected recovery and ownership review.
- Done: monitoring and selected guest roles, partial foundation discovery.
- Missing/components: choose DNS/Caddy, Infisical, Forgejo or storage configuration
  based on recovery criticality; distinguish declarative settings from DB state.
- Deliverables: per-service discovery -> model -> adopt -> check -> review ->
  converge -> legacy cleanup last; backups remain essential.
- Acceptance: working contracts preserved, no duplicate owners, verified restore
  before removing manual/legacy path. No broad replacement for cosmetic consistency.
- Risk: outages and accidental changes to permissions/identities.
- Production changes: yes, one reviewed service at a time.
  Approval: separate service-specific adoption and convergence authorization.

## M15: Hardware replacement and eventual publication

- Objective: prove portability/recovery under real capability changes, then share
  only stable components. Split these into separate execution milestones.
- Prerequisites/dependencies: M9, M12-M14; compatible spare capacity and test plan.
- Done: hardware mappings explicit, not universally portable.
- Missing/components: replacement Proxmox setup, GPU/USB/CPU profile validation,
  bootable workstation images, isolated restore timing and independent users/docs.
- Deliverables: replacement evidence first; optional versioned component release later.
- Acceptance: required workloads recover on changed hardware with measured limits;
  two proven consumers/profiles justify extraction; public examples contain no secrets.
- Risk: passthrough incompatibility, resource contention, premature multi-repo releases.
- Production changes: potentially high for eventual hardware cutover; not for publication.
  Approval: explicit drill/cutover approval; external repository authorization separately.

## Critical path and deferrals

First independently recoverable CI/CD deployment: M1 -> M2 -> M3, foundation
recovery M5, candidate gates M6/M7 -> M8, isolated recovery M9 -> canary M10 ->
protected CI/CD M11. M4 can run alongside recovery work. M12-M13 portability
work is useful but does not need to block safeguarding state or proving recovery.

Defer broad runner naming cleanup, all-service generic modules, multi-repository
publication, automatic scheduling, fleet-wide hardware changes and cosmetic
documentation rewrites. Garage backend rejection needs no further experimentation.
Do not confuse deferral with permission to ignore the exporter-role defect,
monitoring trust failure, state custody or shared runner privilege boundary.
