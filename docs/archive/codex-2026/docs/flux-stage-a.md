# Stage A Flux disposable demo

Task [120](../tasks/120-gitops-stateless.md#live-disposable-milestone---2026-10-02)
records the live-verified bootstrap, healthy demo and Git-driven revision1-to-2
change. Broader exercises remain open; CI alone is not live evidence.
No Homepage, storage integration, production ingress or data migration.

## Pins and provenance

- Flux v2.9.5, source-controller and kustomize-controller v1.9.5 only.
  [Official release](https://github.com/fluxcd/flux2/releases/tag/v2.9.5) reviewed;
  [supported Kubernetes versions](https://fluxcd.io/flux/installation/) include1.35.
- Export produced by the official darwin_arm64 CLI archive, SHA256
  `2869ef7151a6f1b27e6b5d2a6804f3ef23c7bdaa06a74e00d3fe5bfc646547fd`,
  checked against official release asset metadata. No signature verification claim.
- Vendored generated `gitops/stage-a/bootstrap/gotk-components.yaml` SHA256
  `ce5ceb48517b29660e493a164f8e22956e4b1e62165989add30829f587d8cb5f`.
  Regenerate only with the reviewed CLI/version and review upstream/RBAC changes:

```sh
flux install --version=v2.9.5 \
  --components=source-controller,kustomize-controller \
  --watch-all-namespaces=false --network-policy=true --export \
  > gitops/stage-a/bootstrap/gotk-components.yaml
```

Never apply that upstream file directly: its default cluster-admin binding is
removed by the bootstrap Kustomize overlay. Controller images are version-pinned;
the BusyBox1.37.0 demo is additionally pinned by the runtime-observed OCI digest.
CI installs checksum-verified kubectl1.35.8 for offline Kustomize rendering; local
qualification uses kubectl1.36.1/Kustomize5.8.1. No CLI is installed on the guests.

## Ownership and access

Ansible owns initial namespaces, CRDs, controllers, RBAC and source registration.
Flux owns ONLY the ConfigMap, Deployment and ClusterIP Service rendered from
`gitops/stage-a/demo`. No self-managing cluster-root Kustomization, Helm controller,
image automation or second application writer. Controller upgrades need a new
reviewed bootstrap change; this command is not an unattended upgrade mechanism.

Source: public Forgejo `Homelab/homelab-iac`, HTTPS, main, anonymous read-only;
no deploy key, PAT, Git credential Secret or bootstrap Git write. Only `/gitops`
is included in the fetched artifact and only the demo path is reconciled.
Any trusted main change in that path is a live demo deployment, including before
quality CI finishes: review pushes accordingly. No privileged infrastructure CD.
Ordinary CI still has no kubeconfig, secret injection or cluster administration.

Upstream cluster roles/bindings are removed. Controllers watch only flux-system;
namespace-scoped roles permit Flux resource/lease handling and read access to
local config/Secrets. There are no production Secrets in this bootstrap. The
kustomize-controller may impersonate only demo-reconciler/default in flux-system.
The former can manage only demo deployments/services/configmaps and read health
metadata in flux-demo; default has no grant. No namespace/RBAC/Secret writes or
cross-namespace resource access for the reconciler. Remote bases and cross-namespace
source references are disabled. See [upstream authorization](https://fluxcd.io/flux/installation/configuration/multitenancy/).

The demo has two small non-root replicas, no token mount, host mounts or persistent
data, read-only rootfs, dropped capabilities and restricted Pod Security admission.
This is scoped Kubernetes authorization, not proof of complete network isolation.
The laboratory still shares one physical failure domain and LAN connectivity.

## Approved operator workflow

Prerequisites: accepted110-A, repository controller dependencies, local kubectl
with Kustomize, strict SSH access to the existing Stage A guests, published reviewed
demo commit and existing authoritative Stage A local state (inventory output only).
No Terraform plan/apply or Infisical credentials are used. Run from the repository:

```sh
make flux-check
make flux-install FLUX_INSTALL_APPROVED=yes
```

Make derives inventory using the existing Stage A validator. Ansible uses the
initial guest's local K3s administration interface over SSH; it does not export
kubeconfig or require the controller's current IP on the API allowlist. Bootstrap
rejects unrelated flux-system namespace ownership and unexpected node identities.
It applies the reviewed overlay, waits for controllers, registers source/sync and
waits for Ready. It never invokes `flux bootstrap`, Git push or credential creation.

Use SSH/local `k3s kubectl` to inspect GitRepository/Kustomization Ready and exact
revision, Deployment readiness, and `auth can-i --as=system:serviceaccount:flux-system:demo-reconciler`.
An operator may port-forward the ClusterIP service through the existing SSH path;
no DNS/Caddy/public route change is needed. HTTP can also be checked inside a demo
pod with `wget -qO- http://disposable-demo.flux-demo.svc.cluster.local:8080`.

Change the page literal in the demo kustomization, review/test/commit/push, then
require source and applied revision to match that commit and verify HTTP content.
Kustomize hashes the ConfigMap name, inducing a rolling Deployment update; Flux
prunes the old demo ConfigMap. Git revert restores the previous desired state.
On unexpected errors, stop; inspect scoped events/logs without Secrets. Suspending
only disposable-demo reconciliation is a separate deliberate write, not a reason
to restart K3s or remove controller storage. No automatic teardown is provided.

Live drills beyond the approved demo (source outage, deliberate drift, forced
rescheduling) require explicit scope; record unperformed criteria as unverified.
