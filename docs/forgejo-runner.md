# Forgejo Runner Target

CT301 remains VMID 301, 192.168.0.31, hostname forgejo-runner-migration.
The operator reports successful convergence and green homelab-iac, CEM, and
theme smoke tests on CT301; CT300 is powered off, not yet retired from state.
Bootstrap/registration procedures below are retained for reference, not steps
to rerun on this working runner. See the [CI/CD state audit and later cleanup
plan](infrastructure-cicd.md) before enabling infrastructure automation.

## Images and connections

One pinned/checksummed Forgejo Runner 13.0.0 daemon runs as runner using
/etc/forgejo-runner/config.yml and /var/lib/forgejo-runner.
Podman is rootful, with a root:podman 0660 socket and runner group membership.
Normal job containers are unprivileged.

| Connection | Forgejo scope | Label | Image |
| --- | --- | --- | --- |
| homelab-iac | Homelab/homelab-iac repository | homelab-iac | git.doku-lab.net/doku-code/ci-base:1.0.0 |
| cem | CEM organization | cem | git.doku-lab.net/cem/cem-ci:1.0.3 |
| forgejo-custom-theme | doku-code/forgejo-custom-theme repository | forgejo-theme | git.doku-lab.net/doku-code/ci-base:1.0.0 |

All three `server.connections.*.url` values must be the Forgejo instance root:
`https://git.doku-lab.net/`. Runner v13 uses this as its API base, not a repository
or organization URL. Repository/organization scope comes from each existing
registration's UUID/token pair. Scoped URL paths cause task-fetch 404 errors;
correcting the URL does not require changing registrations, credentials, labels,
or images.

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

The manual workflow is for releases after the runner is online. First publication
uses the one-time controller procedure below, not another Forgejo connection.
After publication, ordinary reconstruction pulls the stored image. No Dockerfile
change or heavier generic toolchain is needed.

## One-time ci-base publication

This is a proposed live operation, NOT performed by repository validation.
Use the controller's existing root SSH access to CT301 and its already-installed
native Podman 5.4.x. There is no local Podman installation, remote-client mismatch,
runner registration, or persistent bootstrap service. Only the committed image
context is exported from this repository; dirty files and .git are excluded.

Reuse the existing CEM publishing PAT only if it has write:package scope AND its
account can publish under doku-code. For a user namespace this means that user;
for an organization it means an account with organization write/admin access.
Publishing CEM successfully does not establish doku-code access. Confirm the
account/scope in Forgejo before proceeding, without exposing the PAT or reading
another repository. If these permissions are absent, stop for an operator decision;
do not automatically create another PAT or broaden permissions.
See [Forgejo package permissions](https://forgejo.org/docs/latest/user/packages/).

Reuse avoids another credential but shares its compromise/revocation impact with
CEM publication. This one-time procedure does not copy it into homelab Actions
Secrets or Infisical. It is entered at a hidden SSH prompt, used via password-stdin,
and stored only in a temporary root-only /run directory, removed on exit. CT301
root can access it during publication, so this requires trusting CT301. The
permanent runner auth remains the separate existing READ credential. Future
automated publication credentials can be decided when that workflow is needed.

In Forgejo first confirm ci-base:1.0.0 is absent. Do not overwrite an existing
release. Review the committed Dockerfile and authorize this build/push separately.
Then run this block in Bash from the homelab-iac root (not with shell tracing):

```bash
(
  set -euo pipefail
  revision=$(git rev-parse HEAD)
  ssh_ct301=(ssh -i "${GUEST_SSH_PRIVATE_KEY_FILE:-$HOME/.ssh/id_ed25519}" root@192.168.0.31)
  git archive "$revision:services/ci-images/base" | "${ssh_ct301[@]}" "
    set -eu
    work=\$(mktemp -d /tmp/ci-base-build.XXXXXX)
    trap 'rm -rf \"\$work\"' EXIT
    tar -xf - -C \"\$work\"
    podman build --platform linux/amd64 --network host \\
      --label org.opencontainers.image.source=https://git.doku-lab.net/Homelab/homelab-iac \\
      --label org.opencontainers.image.revision=$revision \\
      --tag git.doku-lab.net/doku-code/ci-base:1.0.0 \"\$work\"
  "
  publish=$(cat <<'REMOTE'
set +x
set -euo pipefail
umask 077
auth=$(mktemp -d /run/ci-base-publish.XXXXXX)
trap 'unset token; rm -rf "$auth"' EXIT
read -r -p 'Existing publisher username: ' username
read -r -s -p 'Existing package-write PAT: ' token
printf '\n'
test -n "$username" && test -n "$token"
printf '%s' "$token" | podman login --authfile "$auth/auth.json" \
  --username "$username" --password-stdin git.doku-lab.net
unset token
podman push --authfile "$auth/auth.json" --digestfile "$auth/digest" \
  git.doku-lab.net/doku-code/ci-base:1.0.0
cat "$auth/digest"
REMOTE
  )
  "${ssh_ct301[@]}" -t "bash -c $(printf '%q' "$publish")"
)
```

Verify the package/manifest in Forgejo and record the digest. Build layers/the
image remain cached on CT301, but are not reconstruction dependencies. Temporary
context/auth files are removed on normal exit, including command failure; after
a killed session verify cleanup of its /tmp/ci-base-build.* and
/run/ci-base-publish.* directories before proceeding. No service is restarted.

## Fresh registrations and operator batches

1. Publication batch: confirm reuse permissions for the existing write PAT;
   authorize and run the one-time procedure above. Verify tag 1.0.0 and its digest.
   No new credential, permanent executor, or Actions Secret is needed for this batch.
2. Registration batch, after the image is ready: create fresh registrations
   together for Homelab/homelab-iac, organization CEM, and
   doku-code/forgejo-custom-theme. Store all six persistent UUID/token values in
   Homelab-IaC dev under /forgejo-runner/connections in one Infisical session:

   | Connection | UUID field | Token field |
   | --- | --- | --- |
   | homelab-iac | HOMELAB_IAC_CONNECTION_UUID | HOMELAB_IAC_CONNECTION_TOKEN |
   | cem | CEM_CONNECTION_UUID | CEM_CONNECTION_TOKEN |
   | forgejo-custom-theme | CUSTOM_THEME_CONNECTION_UUID | CUSTOM_THEME_CONNECTION_TOKEN |

   Before the completed migration, CEM/custom-theme tokens were CT300 legacy
   values and their UUIDs and both homelab fields were empty. Reconstruction
   uses the working CT301 pairs now stored in Infisical; do not replace these
   identities merely to enable CI/CD. For a separately approved fresh replacement,
   populate every field from its three fresh registrations.
   Do not confuse registration bootstrap tokens with persistent connection tokens.
   No controller-local UUID file is required: Git + Infisical + Forgejo are the
   reconstruction sources. Ansible rejects missing/blank tokens, missing/invalid
   UUIDs, nil UUIDs, and duplicate UUIDs before the role mutates CT301. It cannot
   prove token provenance or pairing offline; fresh registration and subsequent
   Forgejo connectivity verification are mandatory. Do not fill new UUIDs beside
   old tokens. There is no CT300 credential fallback.

3. Review/convergence batch: with controller Universal Auth credentials exported,
   run make runner-live-check.
   Review the diff and verify private pulls with the existing read identity.
   Only after approval run make runner-migration-configure.
   Smoke-test homelab validation, CEM workload authentication, theme behavior,
   private image pulls after reboot, and absence of automatic socket/secret mounts.
   No live check or convergence is performed in this repository-only milestone.

Offline regression validation is available with
`.venv/bin/python tests/runner-connections.py`. It executes only extracted
assert/map tasks and template rendering on localhost with synthetic secrets;
it never authenticates to Infisical or runs the host role.

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
