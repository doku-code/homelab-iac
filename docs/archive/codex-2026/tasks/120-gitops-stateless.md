# 120 - Flux, first disposable workload and measurements

- Status: LIVE VERIFIED for the approved disposable Flux milestone (2026-10-02):
  installation, source/controllers, demo and one Git-driven change passed.
  Broader exercise criteria below remain OPEN, not silently marked complete.
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
in CI. Next [125 fresh Homepage](125-homepage.md);130 waits for NAS readiness,
not the first stateful workload. Initial persistence follows the
[node-local contract](../docs/architecture.md#initial-development-storage).
No stateful cutover. The
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

## Live disposable milestone - 2026-10-02

The earlier SSH blocker is resolved: strict authenticated SSH returned the three
expected hostnames; all nodes were Ready at v1.35.8+k3s1. No network, trust,
Terraform, K3s configuration or service restart was needed. No existing Flux
namespace was present before bootstrap.

Publication gate:

- Requested a80e60cc29044ad3cceb270e7045fb6b9b57d327 pushed; GitHub main matched.
  Forgejo run42/API153 FAILED at the Stage A test's global Makefile inventory
  count, which now also counted the Tailscale target. Not a Flux/runtime failure.
- d908ce054cb00b3e3123b3f165e9fd4d5bdcff24 scoped the assertion to each of the two
  Stage A recipes, retaining the guard. Local Stage A tests passed, Forgejo
  run43/API154 succeeded and GitHub main matched before live installation.

`make flux-install FLUX_INSTALL_APPROVED=yes` completed:
**ok=10 changed=2 unreachable=0 failed=0**. Source-controller and
kustomize-controller v1.9.5 each became 1/1 Ready with zero restarts. Anonymous
Forgejo GitRepository and disposable-demo Kustomization became Ready at d908ce0.
No privileged Git credentials, source Secret or controller kubeconfig export.

The two digest-pinned BusyBox replicas initially ran on server-2/server-3;
ClusterIP/service DNS HTTP returned `Stage A Flux demo - revision 1`.
Published bde0e7c0c7282a436dc50f652f3edb38194ac01d changed only the page literal.
Forgejo run44/API155 succeeded for this exact SHA and GitHub main matched it.
Normal polling, without a forced reconcile or manual app apply, produced:

- Source artifact and last applied revision both
  `main@sha1:bde0e7c0c7282a436dc50f652f3edb38194ac01d`, Ready.
- Deployment 2/2, new replicas on server-1/server-2, zero restarts.
- Both individual pod HTTP responses and service-DNS HTTP returned revision2.
- ConfigMap `demo-page-8728488c8t` replaced by `demo-page-fbgkmdh9kf`;
  the old generated ConfigMap was pruned by Flux.

Read-only impersonation checks: demo-reconciler can create deployments in
flux-demo; denied in default, denied Secrets reads in flux-demo, denied
ClusterRoleBinding creation. These checks are not proof of network isolation.
Point-in-time node CPU was28/29/35m, memory944/901/958Mi (24/22/24 percent).
Controller samples: kustomize3m/76Mi, source1m/35Mi. These are basic headroom
observations, not sustained-load or 24-hour capacity qualification.

Approved milestone criteria:

- [x] Reviewed existing bootstrap installed; two healthy pinned controllers.
- [x] Anonymous Forgejo source and namespace-scoped app reconciliation.
- [x] Healthy disposable app and verified Git-driven HTTP/configuration change.
- [x] Scoped RBAC denial and basic resource observations.
- [x] No extra disposable validation resources created; no manual cleanup needed.
- [ ] Deliberate drift correction, Git revert, source outage/recovery and forced
  pod rescheduling remain unperformed; normal rolling replacement is not those drills.

Local `make flux-check` passed before install and before the page change
(render/pins/RBAC/source/approval regressions and Ansible syntax).
No Homepage, NAS, persistent storage, physical topology or recovery changes.
The demo remains as declared in Git; no teardown is defined or performed.
The bounded disposable milestone is complete; Task120's broader exercises remain
open under separate approval. Next single application task:125 fresh Homepage;
do not begin it in this session.
