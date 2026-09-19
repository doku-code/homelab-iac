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
the observed values are recorded in the root's example variables file.

The existing CT is VMID `300` on `pve-compute`, with 4 cores, 6144 MiB RAM,
512 MiB swap, a 38 GiB `local-lvm` rootfs, `vmbr0`, nesting, and an
unprivileged configuration. Its historical template provenance is not
recoverable from the CT config. Proxmox currently offers
`pve_library:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst`, which is the
canonical reconstruction template for future creates, not the asserted
historical source.

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
runtime policy, and filesystem permissions. The role models the two observed
daemon purposes as reusable instances over Podman: the root-owned
multi-connection `cem`/`theme` daemon and the separate
`forgejo-custom-theme-runner` daemon. The live binary is `13.0.0`; the
service model keeps one-job capacity, non-privileged job containers, and
explicit rootful Podman socket selection. It does not overwrite live
configuration until the external secret inputs and ownership boundaries are
reviewed.

Use `make runner-check` for syntax validation, `make runner-plan` for the
backend-free Terraform root, and `FORGEJO_RUNNER_HOST=... make
runner-configure` only when deliberately configuring the existing guest.
Docker Compose is not used because the runner's lifecycle is not containerized
by this repository.

Do not recreate or re-register the existing runner as part of repository
changes. Registration is a one-time manual Forgejo operation after the role has
installed the binary and stopped services. Register each required instance in
Forgejo, then enable and start the corresponding services on the guest. The
registration tokens and generated state files must stay outside Git,
preferably in the Forgejo administration flow or a protected secret store.

## Live Topology And Migration Map

`forgejo-runner.service` runs as `root`, uses the rootful
`/run/podman/podman.sock`, and contains two Forgejo connections: `cem` with
the `cem-latest` label and local `cem-ci` image, and `theme` with a Node
22 job image. `forgejo-custom-theme-runner.service` runs as `runner`, has a
separate theme registration and Node 20 label, and currently fails because it
points to the rootful socket without effective `podman` group access. It is
repeatedly restarted by systemd and must not be disabled or removed as part of
adoption.

Terraform owns CT 300 infrastructure and its bounded resources. Ansible should
own the Podman prerequisites, runner binary, daemon units, non-secret config
shape, ownership, and socket permissions. Forgejo owns registrations and
workflow routing. Infisical should become the future owner of runner,
Infisical, CEM, theme, and registry credentials. Existing secret-bearing files
remain on the guest until a later migration proves replacement behavior.

The CEM image is currently a manually maintained local `cem-ci:latest` image
built from `/opt/cem-ci-image/Dockerfile`. Its context contains only that
Dockerfile, and no secret-bearing files were observed in the context listing.
The Dockerfile uses Node 22 Bookworm and installs pinned Gitleaks and Infisical
tooling. It is a suitable candidate for a future repository-owned image, but
should first be copied into Git after reviewing the complete build definition
and then published by protected CI with immutable commit-SHA tags. No image was
rebuilt or pushed during this milestone.

## Import And Authentication Status

The safe Terraform import address is
`proxmox_virtual_environment_container.forgejo_runner` and the provider
import identifier is `pve-compute/300`. Import was deliberately deferred: the
workstation shell had no Proxmox provider credentials, and the historical
template source is unavailable. The existing local operator abstraction is
the `INFISICAL_RUN` Make function, which obtains a short-lived Infisical token
from Universal Auth and injects runtime variables. Extend that abstraction for
the runner root only when the required Machine Identity credentials are
available; do not introduce a human Infisical session or a second auth path.

Before import, confirm the private variables file, provider credentials,
canonical template choice, and expected provider normalization. Then run
`terraform state show` and a normal plan. Any replacement, disk, network,
privilege, or mount change requires investigation before proceeding.

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

### Repository-Scoped CI Bootstrap

Forgejo Actions repository secrets are server-side configuration and are not
copied into clones, forks, Git history, GitHub mirrors, or tags. Each trusted
repository receives only its own Infisical Universal Auth bootstrap pair:

```text
INFISICAL_CLIENT_ID
INFISICAL_CLIENT_SECRET
```

The Homelab-IaC repository uses these secrets only in protected workflows that
need infrastructure access. The validation workflow does not receive them.
Non-secret metadata such as the project ID from `.infisical.json`, the `dev`
environment, the Infisical domain, and secret paths is versioned configuration.
External repositories and arbitrary pull requests must not receive homelab
infrastructure credentials merely because they use the same physical runner.

### Runner Infrastructure Secrets

The three Forgejo connection credentials used by the adopted runner are
infrastructure secrets, not CEM or theme application secrets. Their canonical
future location is the Homelab-IaC Infisical project:

```text
/forgejo-runner/connections/CEM_CONNECTION_TOKEN
/forgejo-runner/connections/THEME_CONNECTION_TOKEN
/forgejo-runner/connections/CUSTOM_THEME_CONNECTION_TOKEN
```

The runner playbook reads these values controller-side with Universal Auth,
maps them into `forgejo_runner_connection_tokens` in memory, and keeps the
secret-bearing template task under `no_log`. It does not use a human Infisical
session, a persistent controller file, or manually exported individual runner
tokens.

The one-time migration helper is deliberately opt-in:

```text
CONFIRM_RUNNER_SECRET_MIGRATION=yes make runner-migrate-secrets
```

It reads the existing live runner configuration under protected tasks, refuses
to overwrite an existing canonical secret, and verifies names after creation.
It does not rotate or re-register runners. The operator must have temporary
write permission for this migration; the normal homelab Machine Identity can
remain read-only afterward. Do not run this helper until the migration is
explicitly reviewed.

### Legacy Runner Mounts

The live files `/etc/forgejo-runner-infisical.env` and
`/etc/forgejo-theme-infisical.env` are legacy project-bootstrap mounts used by
existing CEM and theme workflows. They remain modeled and mounted for behavior
preservation. Do not remove them until the external CEM and
`forgejo-custom-theme` workflows have independently migrated to their own
Forgejo repository secrets and Universal Auth projects, and their jobs have
been verified successfully.

Those external repositories are not part of this checkout, so this repository
does not claim that their workflow migration is complete. Their required
change is to reference their own repository secrets, authenticate to their own
Infisical project, and stop depending on the runner-mounted project bootstrap
files before the mounts are retired.

### Trust Boundary

Forgejo is the trusted operational Git and CI control plane. GitHub is an
outbound mirror or publication surface by default. Code from forks, external
upstreams, or other unadopted repositories is untrusted and must not run with
infrastructure or deployment credentials. Separate low-privilege validation
from protected deployment workflows.

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
