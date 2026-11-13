# Fresh Stage A Homepage

Task [125](../tasks/125-homepage.md), fresh phase only. No CT201 inspection or copy,
production route, persistent storage, discovery credentials or infrastructure API
access. Live evidence belongs in the task.

## Source and ownership

Reviewed on2026-10-02: maintained upstream [Kubernetes installation](https://gethomepage.dev/installation/k8s/),
[configuration](https://gethomepage.dev/configs/), [discovery modes](https://gethomepage.dev/configs/kubernetes/)
and [v2.4.0 release](https://github.com/gethomepage/homepage/releases/tag/v2.4.0).
Official GHCR index digest verified against downloaded manifest bytes:
`sha256:643bd0be730d40f69d58028a55d1a896739333e8815786df42bc97f109ecbe61`.
The linux/amd64 child is
`sha256:1c7732541505c18a8f6e82fc6afbcdbed7316491bcc538930d518381056c4b56`.
This verifies the registry manifest, not an upstream signature.

Ansible registers only the Homepage namespace, scoped reconciliation RBAC and
Flux Kustomization. Existing Flux controllers and anonymous Forgejo main source
are reused unchanged. Flux owns the app's ConfigMap, Deployment and ClusterIP
Service under `gitops/stage-a/homepage`; no second application writer.
The reconciler has no Secret, RBAC, PVC or cross-namespace write permission.
Homepage itself has no service-account token or Kubernetes discovery access.

One non-root replica, restricted security context and read-only rootfs. Git
provides all nine config files through a hashed ConfigMap mounted read-only at
`/app/config`. Logs go to stdout; bounded emptyDir cache/tmp are disposable.
No PVC/PV/hostPath/node affinity. A recreated pod reconstructs config from Git.
One replica may briefly be unavailable during recreation; this is not HA.

## Commands and test access

From the repository's existing controller:

```sh
make homepage-check
# Publish reviewed manifests first, then use separately authorized live approval:
make homepage-install HOMEPAGE_INSTALL_APPROVED=yes
```

Make uses only existing local Stage A inventory outputs, strict SSH and guest-local
K3s administration. No plan/apply, exported kubeconfig or shared-runner access.
The playbook refuses unrelated namespace ownership and unexpected node identities.

No Ingress, NodePort or external load balancer. For optional browser access, keep
these two terminals open, then close them to remove the temporary forwarding:

```sh
# Terminal 1: bind only guest loopback.
ssh -o StrictHostKeyChecking=yes debian@192.168.0.33 \
  'sudo -n k3s kubectl -n homepage port-forward --address=127.0.0.1 svc/homepage 13000:3000'
# Terminal 2: bind only controller loopback.
ssh -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -N \
  -L 127.0.0.1:3000:127.0.0.1:13000 debian@192.168.0.33
```

Open `http://127.0.0.1:3000`. Host validation allows loopback, the exact Service
DNS name and downward-API pod IP for probes, never a wildcard. This is not an
authentication system or network-isolation claim. Do not expose the app publicly.
Startup/readiness/liveness use upstream `/api/healthcheck`; verify HTTP page
content as well. No host/service integration is enabled merely by running in K3s.

Config changes create a new ConfigMap name and a normal rollout through Flux.
Review/test/commit/push only the intended app change; trusted main writes to this
path deploy live before CI necessarily finishes. CI remains offline/secretless.
An image update requires reviewing release notes, digest, tests and live health.

## Configuration and next comparison

- `settings.yaml`: title, layout, theme and global behavior.
- `services.yaml`: groups, links and optional service widget definitions.
- `bookmarks.yaml` and `widgets.yaml`: shortcuts and information widgets.
- `custom.css` / `custom.js`: optional deliberate UI customization.
- `kubernetes.yaml`, `docker.yaml`, `proxmox.yaml`: integrations disabled/empty
  now; do not enable discovery or mount a socket without separate review.
- Future credentials must use separately approved Kubernetes Secrets/environment
  injection (upstream HOMEPAGE_VAR_/HOMEPAGE_FILE_ substitution), never ConfigMap
  literals or copied private files. No secrets are needed for this phase.

Next separately authorized read-only CT201 inspection should compare used groups,
links, widgets, custom assets/scripts, metrics endpoints, network/auth dependencies,
secret *names and scopes*, and actual user-facing behavior. Inventory functions,
not the old filesystem. Decide omissions and adapt this fresh deployment through
Git; production DNS/auth/cutover remain separate. No CT201 evidence collected here.
