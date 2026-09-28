# 120 - Flux, first disposable workload and measurements

- Status: PLANNED after110 acceptance A and Git/source/RBAC decisions reviewed.
- Deliverable: one reviewed Flux entry point, stateless public demo, bounded
  resource observations; extended measurements tracked for later placement.
- Scope: code-only first; explicit approval for Flux bootstrap Git writes,
  identity provisioning, cluster convergence and test-only ingress.

2026-09-28 sequencing: develop on usable Stage A first, without waiting for
140-B physical placement,110 advanced drills, full040, backend or protected CD.
Neither path bypasses110 acceptance A.
Physical stages are topology, not credential sources. Follow045 input contracts;
Infisical is optional operator delivery, not a prerequisite for the public demo.

Use pinned Flux controllers/manifests. Prefer existing homelab-iac paths for
environment-specific GitOps composition, not a new repository framework. Inspect
generic bootstrap's Git-write effects; operator bootstraps reviewed manifests,
then runtime source access is read-only. Public source can avoid read credentials
where appropriate. No competing Ansible/Helm/Terraform app writer. Protect the
reconciled ref and restrict Kubernetes RBAC by scope; no runner kubeconfig.

Deploy pinned public stateless demo, no production data/secrets; readiness,
resource requests/limits, replicas and placement explicit. Port-forward first;
any ingress chart, bundled-component disable and route test requires reviewed
ownership. No production DNS or Caddy changes. Do not automate image updates.
Prototype selected Infisical integration only with separately approved synthetic
identity and prove denied cross-scope access; production sync is a later gate.

Acceptance: offline render/schema checks at pinned versions and CI; live Flux
source/health and drift correction; Git revert restores demo; denied unauthorized
namespace access; source outage/recovery; bounded disposable pod rescheduling
without a member-failure drill. Record basic resource/headroom observations
before adding the next app; workstations remain off during Stage A.
Representative 24-hour measurements remain a separate capacity qualification
before real-workload physical-placement acceptance, not a fresh Homepage gate.
Retain existing outside monitoring; do not refactor live monitoring in this task.

Rollback: suspend affected reconciliation, restore reviewed commit/bootstrapped
manifests; no data loss possible by scope. No host socket or production credentials
in CI. Next [125 fresh Homepage](125-homepage.md);130 is demand-driven by the
first stateful workload, not every app. No stateful cutover. The
independent150 pve-infra assessment must not wait for this experiment.
