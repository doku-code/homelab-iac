# 080 - Requirements-led state backend and protected infrastructure CD

- Status: PLANNED; replaces the mandatory060/070 comparison and old080 sequence.
- Permission: decision/documentation first; each implementation/live phase separately assigned.
- Dependencies: real need for additional infrastructure writers;010/020 security closure,
  portable050, relevant040 material and production recovery evidence from140.
- Deliverable: justified authority/locking model, then qualified protected automation.
  Neither is required for disposable Stage A learning.

## A - Decide from requirements

Inventory actual writers, concurrency, accepted backend outage, recovery time,
credential custody, operational burden and one-authority rules. Keep local
single-operator state while adequate; no cloud sync or copies as active backend.
Recommend external PostgreSQL only if shared locking is required and remaining
TLS/identity/recovery gates can be met simply.060 provides conditional evidence,
not an automatic winner. Consul070 is optional only for a demonstrated need,
not a required learning detour. Garage's failed native-lock result stays rejected.
No Kubernetes-hosted bootstrap backend that depends on its own cluster.

## B - Qualify selected candidate in isolation

After explicit operator selection, scope TLS verify-full/negative trust tests,
separate operator/CI least-privilege identities and source restrictions, true
two-client lock exclusion, crashed-client recovery, root isolation, independent
backup and full isolated restore at the final endpoint. No production state
migration or credential creation implicit. Stop on locking/recovery failure.

## C - Separate canary migration task

Choose one non-bootstrap root only after accepted B and recovery evidence.
Freeze/fence writers, seal exact authority, verify lineage/serial/destination,
approve migration explicitly; prove no unintended resource replacement and
shared lock behavior, designate exactly one writable destination. No module
refactor in that change. Rollback must reconcile post-migration writes and
fence remote writer before any local authority resumes.

## D - Protected infrastructure CD, separate from Flux apps

Only after010 security closure and C: narrow root allowlist, protected reviewed
refs, short-lived scoped auth, mandatory state, expiring exact saved plans and
explicit approved apply window. No infra secrets in ordinary quality job, no
socket escalation to bypass isolation. Negative tests deny untrusted refs,
wrong root, missing/stale plan and concurrent writers. Flux reconciles Kubernetes
apps under separate scoped review; it never applies Proxmox state.

Rollback: disable privileged workflow first, recover authority through reviewed
procedure, never fall back automatically to stale local state. Accept each phase
separately with actual evidence. No automatic next apply or new backend service.
Historical qualifications remain in060/070 and docs; old080-B recovery scope is
now140-C, not a competing roadmap.
