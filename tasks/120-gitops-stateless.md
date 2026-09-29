# 120 - Flux, first disposable workload and measurements

- Status: BLOCKED on SSH reachability to Stage A;110-A accepted and the bounded
  Flux/demo installation authorized. Repository implementation/CI passed; no live
  Flux installation or application reconciliation performed yet.
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

## Implementation scope - 2026-09-29

See [Stage A Flux runbook](../docs/flux-stage-a.md). Two pinned controllers only;
anonymous Forgejo main source, one narrow demo path, namespace-scoped RBAC and
non-root digest-pinned BusyBox HTTP workload. Ansible bootstrap via existing SSH,
no exported kubeconfig/privileged Git credentials or writes by Flux to Git.
Initial implementation and CI are not live reconciliation evidence. Latest
approval covers installation, app health and one Git-driven configuration change;
source-outage/drift/revert/rescheduling exercises remain unverified unless
separately authorized. No synthetic Infisical identity is needed or created.

## Delivery and access boundary - 2026-09-29

Task110 evidence commit3c2d583f42e3489bbec3bfc2f915f2944a21c6f7 passed Forgejo
run39/API150 and matched GitHub before Task120 implementation began. Advanced
Task110 drills remain open; successful cluster qualification was not repeated.

Implementation801d1f69b9693dfc9f0a87590e76cd6dbfde70a6 passed Forgejo run40/API151;
GitHub main matched exactly. Local Flux render/RBAC/source/approval tests and
Ansible syntax passed; YAML/Python/shell parsing and diff checks passed. Ansible
syntax needed normal local temp permissions outside the restricted sandbox.
CI tested the new manifests offline with pinned kubectl; no cluster credentials.

Live pre-install namespace inspection could not connect: strict SSH to .33 timed
out, as did bounded10s checks to .34 and .35. The local route to .33 uses en0;
this is not proof of guest, host or network failure cause. No trust/authentication
bypass, infrastructure change or Flux resource creation attempted. Anonymous
Forgejo Git read succeeded without credential helpers. No new privileged Git
credential is required.

Next operator action: restore this controller's SSH reachability to the three
existing guests. Then resume the already-approved `make flux-install
FLUX_INSTALL_APPROVED=yes`, verify source/application/RBAC and one reviewed
Git-driven demo page change. Do not start Homepage or mark Task120 DONE from CI.
