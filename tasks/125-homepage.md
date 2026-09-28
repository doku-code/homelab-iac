# 125 - Fresh declarative Homepage

- Status: PLANNED; no implementation or live operation authorized here.
- Dependencies: Task110 acceptance A and Task120 disposable Flux demo accepted.
- Scope: first real application, fresh and disposable; no CT201 migration.

Follow the [application development pattern](../docs/roadmap.md#application-development-pattern).
Read maintained upstream documentation; select a pinned image and clean manifests
or a maintained chart in the existing GitOps layout. Deploy a new empty Homepage
through Flux and verify it before targeted, separately authorized read-only CT201
inspection. Existing Task150 inventory is a lead, not full configuration evidence.

Identify the dashboards, widgets, images, metrics and dependencies actually used.
Adapt the versioned fresh deployment to those functions; do not copy CT filesystems,
private configuration or historical runtime choices. Credentials stay outside Git,
are scoped to the needed widgets and require separate provisioning approval.
Do not expose a host socket or reuse privileged credentials merely for a widget.

Acceptance:
- Pinned declarative deployment passes offline render/schema and secret checks.
- Flux reconciles a healthy fresh instance using internal test access; no live DNS
  cutover, production credentials or persistent storage required by default.
- A concise feature/dependency comparison identifies observed CT201 behavior,
  intentionally retained functionality and operator-accepted omissions.
- Required functions work in the new instance with bounded resource use; Git
  revert/reconciliation is verified and CT201 remains unchanged and available.
- Record actual validation and operator acceptance before choosing the next app.

If a real persistence requirement appears, scope Task130 to it rather than
silently depending on local durable data. Final data migration, DNS switch and
retirement are separate approvals under140-C/150, not acceptance of a fresh app.
Next: choose one suitable service; Wiki.js is an early stateful candidate after
minimal applicable TrueNAS CSI qualification. Do not automatically start it.
