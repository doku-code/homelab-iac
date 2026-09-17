# Forgejo Runner Architecture

## Current Repository Facts

The repository currently contains one workflow: `.forgejo/workflows/validate.yml`.
It is validation-only and requests the `docker` runner label. Jobs run inside a
container and do not receive Proxmox, Infisical, registry, or deployment
credentials.

The existing runner is represented by the parameterized Terraform root
`terraform/stacks/pve-compute-forgejo-runner/` and configured by the
`forgejo_runner` Ansible role. The live VMID, placement details, network,
storage, allocations, and container engine still require operator inspection;
none are guessed in Git.

Terraform adoption is intentionally a separate import step. Collect the live
CT configuration, create a private `terraform.tfvars`, import
`pve-compute/<VMID>`, and review a normal plan before any apply. The resource
has `prevent_destroy = true`.

## Intended Separation

The `docker` label is reserved for ordinary validation jobs:

- checkout and dependency setup;
- Terraform formatting and backend-free validation;
- Ansible syntax checks;
- Compose validation and future tests;
- no homelab credentials or live infrastructure access.

A future deployment runner should use a separate protected label such as
`homelab-deploy`. It should be used only by manually dispatched or otherwise
protected deployment workflows, with the smallest required access to Proxmox,
Infisical, and target hosts. It must not be required by validation workflows.

Using one physical runner for both labels is acceptable as a temporary
arrangement, but the job labels and workflow permissions should preserve the
conceptual separation from the beginning.

## Runner Host Ownership

Ansible owns runner package installation, service configuration, container
runtime policy, and filesystem permissions. The initial role defaults to
Forgejo Runner `13.1.0`, one job, the `docker` label mapped to
`node:24-bookworm`, Docker execution, bridge networking, no privileged mode,
and no valid host-volume mounts. The service is left stopped until its
one-time registration is complete. Override these values only after verifying
the live runner and host assumptions.

Use `make runner-check` for syntax validation, `make runner-plan` for the
backend-free Terraform root, and `FORGEJO_RUNNER_HOST=... make
runner-configure` only when deliberately configuring the existing guest.
Docker Compose is not used because the runner's lifecycle is not containerized
by this repository.

Do not recreate or re-register the existing runner as part of repository
changes. Registration is a one-time manual Forgejo operation after the role has
installed the binary and stopped service. Register it in Forgejo, then enable
and start `forgejo-runner.service` on the guest. The registration token and generated
`/var/lib/forgejo-runner/.runner` configuration must stay outside Git,
preferably in the Forgejo administration flow or a protected secret store.

Normal CI runners should use isolated job containers without privileged mode,
host networking, arbitrary host mounts, or `/var/run/docker.sock`. A separate
build runner or an explicitly reviewed rootless image-building mechanism is
required before workflows publish OCI images.

## Infisical CI Model

The dedicated Forgejo deployment identity should use least-privilege access to
only the environments and paths needed by deployment workflows. Forgejo should
store only the Universal Auth bootstrap credentials required to obtain a
short-lived token. The actual infrastructure and application secrets remain in
Infisical.

The current validation workflow intentionally does not authenticate to
Infisical. The local Terraform Make workflow uses Universal Auth runtime
variables. A future deployment workflow should use the same underlying model,
with `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET` supplied as protected
Forgejo secrets and never echoed in logs.

## Registry Decision

No repository-owned image currently exists that justifies registry publishing.
The Forgejo OCI registry is therefore intentionally not wired into CI yet.
When a real image is introduced, publish it under the repository namespace
with an immutable commit-SHA tag; optional human-friendly tags may point to the
same artifact. Registry credentials must be limited to the build workflow.

## One-Time Live Bootstrap and Checks

Before enabling deployment workflows, inspect and document the live Forgejo
runner settings:

1. Confirm Actions is enabled and the `docker` runner label is online.
2. Confirm jobs execute in isolated containers rather than on the runner host.
3. Confirm privileged mode, host networking, broad mounts, and Docker socket
   access are disabled for validation jobs.
4. Identify the runner host and decide whether Ansible should manage it.
5. Register a separate protected deployment label only after its access scope
   and approval path are defined.
6. Add the dedicated Infisical identity to protected Forgejo secrets without
   exposing its client secret in workflow output.

These checks require Forgejo administration or live host access and were not
performed by repository-only validation.
