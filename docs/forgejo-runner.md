# Forgejo Runner Target

CT301 remains VMID 301, 192.168.0.31, hostname forgejo-runner-migration.
This repository prepares its configuration; live configuration is not yet
approved. CT300 and both Terraform states remain unchanged.

## Images and connections

One pinned/checksummed Forgejo Runner 13.0.0 daemon runs as runner using
/etc/forgejo-runner/config.yml and /var/lib/forgejo-runner.
Podman is rootful, with a root:podman 0660 socket and runner group membership.
Normal job containers are unprivileged.

| Connection | Forgejo scope | Label | Image |
| --- | --- | --- | --- |
| homelab-iac | Homelab/homelab-iac repository | homelab-iac | git.doku-lab.net/doku-code/ci-base:1.0.0 |
| cem | CEM organization | cem | git.doku-lab.net/cem/cem-ci:1.0.1 |
| forgejo-custom-theme | doku-code/forgejo-custom-theme repository | forgejo-theme | git.doku-lab.net/doku-code/ci-base:1.0.0 |

CEM is an organization. Its image is owned by CEM/ci-template, outside this
repository's authorization boundary. No local checkout is needed to rebuild CT301.
ci-base supplies common tools; specialized tools such as Terraform and Ansible
remain installed by their workflows. Theme compatibility is a smoke-test
assumption: the external repository was not inspected.

## Registry authentication

Universal Auth runs on the controller with INFISICAL_CLIENT_ID and
INFISICAL_CLIENT_SECRET. Project metadata comes from .infisical.json, environment
dev. Existing /forgejo-runner/registry secrets REGISTRY_USERNAME and
REGISTRY_READ_TOKEN are the only host registry credentials.

Ansible writes Docker-compatible auth JSON at
/etc/forgejo-runner/registry/config.json, runner:runner 0600, in a root:runner
0750 directory. Secret tasks use no_log and disable diffs. Declarative copy
updates only when credentials change; podman login validates stored credentials
without supplying replacement credentials. The persistent file survives reboot.
The runner service sets DOCKER_CONFIG and REGISTRY_AUTH_FILE to this location;
rootful Podman commands use --authfile explicitly. The runner's Docker API client
can send registry auth to the rootful engine for private image pulls.
No workload Universal Auth credentials or publisher credentials are stored here.

The same read identity must have access to both cem/cem-ci and doku-code/ci-base.
That access is not proven by checking names or by syntax validation; verify both
pulls after publication. Do not request a second read credential preemptively.

## Socket boundary and publication

DOCKER_HOST selects the engine for the daemon; container.docker_host is "-" to
prevent automatic socket mounts in ordinary jobs. The exact Podman socket path
is allowlisted so the trusted manual publisher can request it explicitly.
Such jobs have root-equivalent access to CT301; the three connections and every
repository using the CEM organization runner must be trusted accordingly.
Labels do not form a security boundary. Do not execute untrusted fork workflows
on this shared runner.

services/ci-images/base/Dockerfile defines ci-base:1.0.0 for linux/amd64.
It contains bash, Git/LFS, curl, CA certificates, jq, OpenSSH, Node 22,
Infisical CLI, and Gitleaks 8.30.1, with no Podman client or secrets.
The manual publish-ci-base.yml workflow installs checksum-pinned Podman remote
5.4.2 in its own public node:22-bookworm job image. It consumes repository
Actions Secrets REGISTRY_PUBLISH_USERNAME and REGISTRY_PUBLISH_TOKEN, using
password-stdin and a temporary auth directory cleaned on exit. No push trigger
exists. Use trusted main only. Do not overwrite release tags; increment the
image version for future releases and record the published digest for rollback.
The base tag, Debian packages and Infisical CLI are not fully content-pinned:
release artifacts are versioned, but rebuilding from source is not bit-identical.

First publication needs an already-online trusted runner scoped to homelab-iac
with label homelab-iac and explicit socket access. The public job image removes
the ci-base dependency, but does not supply a registered runner.
If none exists, agree a one-time publication runner/controller bootstrap before
dispatch. Do not configure CT301 or change CT300 implicitly to resolve this.
After publication, ordinary reconstruction pulls the stored image.

## Fresh registrations and operator batches

1. Publication batch: add REGISTRY_PUBLISH_USERNAME and REGISTRY_PUBLISH_TOKEN
   as homelab-iac Actions Secrets with package-write access to doku-code.
   Push reviewed commits, confirm the trusted publication executor above, and
   manually dispatch Publish CI base image. Verify tag 1.0.0 and retain its
   digest. No credentials are being requested or created by this change.
2. Registration batch, after the image is ready: create fresh registrations
   together for Homelab/homelab-iac, organization CEM, and
   doku-code/forgejo-custom-theme. Store their persistent connection tokens in
   Homelab-IaC dev under /forgejo-runner/connections as
   HOMELAB_IAC_CONNECTION_TOKEN, CEM_CONNECTION_TOKEN, and
   CUSTOM_THEME_CONNECTION_TOKEN. Do not copy CT300 identities or confuse
   registration bootstrap tokens with persistent connection tokens.
   Record their fresh UUIDs in an operator file, for example
   runner-connections.secrets (ignored), structured as:

       forgejo_runner_connection_uuids:
         homelab-iac: <fresh UUID>
         cem: <fresh UUID>
         forgejo-custom-theme: <fresh UUID>

3. Review/convergence batch: with controller Universal Auth credentials exported,
   run make runner-live-check RUNNER_CONNECTION_UUIDS_FILE=runner-connections.secrets.
   Review the diff and verify private pulls with the existing read identity.
   Only after approval run make runner-migration-configure with the same file.
   Smoke-test homelab validation, CEM workload authentication, theme behavior,
   private image pulls after reboot, and absence of automatic socket/secret mounts.
   No live check or convergence is performed in this repository-only milestone.

## Later Terraform promotion

After successful smoke tests and explicit decommission approval:
back up both private state files and CT300 data; stop/retire old registrations;
review a CT300-only destruction plan (including its prevent_destroy guard).
Remove CT300 deliberately, then archive its now-empty Terraform state/root
privately. Do not use state rm to disguise a live CT or discard its state early.

Move the CT301 root, lockfile, private variables and its own state together to
the vacated canonical pve-compute-forgejo-runner location. Preserve the resource
address and state lineage; update Make/CI/docs paths. For a remote backend use
init -migrate-state with explicit review; these local states must never be merged.
Run init/validate/plan and require zero recreation before any further change.
Change hostname/tags to production in a separate reviewed plan; apply only with
approval and a maintenance window if required. Keep VMID/IP unchanged.

The archived forgejo-runner-history.md records CT300 adoption history.
Legacy secret-migration and per-daemon configuration entry points are retired.
