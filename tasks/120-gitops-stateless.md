# 120 - Flux, first disposable workload and measurements

- Status: PLANNED after110 accepted and Git/source/RBAC decisions reviewed.
- Deliverable: one reviewed Flux entry point, stateless public demo, bounded
  monitoring and 24-hour representative capacity evidence.
- Scope: code-only first; explicit approval for Flux bootstrap Git writes,
  identity provisioning, cluster convergence and test-only ingress.

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
namespace access; source outage/recovery; pod rescheduling with one member lost.
Observe memory/CPU/etcd latency/disk plus demo latency and workstation coexistence
over a representative 24 hours. Set measured budgets/alerts before adding apps.
Retain existing outside monitoring; do not refactor live monitoring in this task.

Rollback: suspend affected reconciliation, restore reviewed commit/bootstrapped
manifests; no data loss possible by scope. No host socket or production credentials
in CI. Next130 and140 read-only capacity planning; no stateful production cutover.
