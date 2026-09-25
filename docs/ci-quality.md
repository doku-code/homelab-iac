# Initial CI quality gate

Status: **FIRST LIVE RUN FAILED; provider-lock correction pending live rerun**.
Operator-run19 at `f341450` executed and failed; earlier local checks passed.
No Forgejo job triggered, live variable/permission changed or push performed by
the agent during this correction. Task010's unresolved trust findings remain.
This is the bounded repository side of tasks 010/020, not production CD.

Read-only follow-up: [task 010 live evidence](../tasks/010-runner-trust-preflight.md)
confirms the effective rootful socket allowlist and unprotected main. The
published workflow at `510d8f1` now has the main-only activation gate. Run17
was skipped by that gate before runner assignment, not by a runner failure.
The operator confirms exclusive push access here; authenticated review of the
other admitted sources remains blocked401. No activation is approved.

## Trust and activation

validate.yml accepts pushes to main and manual dispatch only. Its job requires
`forgejo.ref == 'refs/heads/main'` AND `vars.CI_QUALITY_APPROVED == 'true'`.
Leave that repository variable unset/false until explicit operator approval.
Its stored value is inaccessible (HTTP401); run17 proves the equality was false,
not whether the variable was absent or had another value. There is no PR, pull_request_target, tag or
arbitrary branch trigger. Do not execute untrusted PR code on this shared runner.

The variable is an activation gate, NOT isolation. A writer can edit the workflow
to remove it or add another workflow on another branch. Main-only triggers alone
cannot protect a runner from repository writers. Before first push/execution,
verify contributor/admin permissions, branch/workflow protections, Actions
settings and all connections admitted to the shared daemon. Current evidence and
remaining UNKNOWN fields are maintained in task 010. No credential was requested.

Source evidence: forgejo_runner defaults grant the daemon Podman group access
and globally permit `/run/podman/podman.sock` as a volume. The template uses
privileged=false, empty container options and docker_host="-"; ordinary jobs do
not automatically mount the socket. The separate publisher explicitly requests
it. One daemon serves homelab-iac, CEM and theme. Labels are not isolation.

The September24 audit and read-only preflight observed an active service and
three root URLs, not safe execution of this new job. Actual job mounts/egress,
Forgejo token capabilities and contributor restrictions remain unqualified. Even without
credentials, jobs may reach the LAN. Secretless does not mean harmless.

The unsupported GitHub-style permissions declaration has been removed; Forgejo
reported it ignored. Removal does NOT impose an equivalent token restriction.
The validation job uses non-persistent checkout auth;
no container/services override, host volumes, socket, privileged option, secret
expression or infrastructure auth wrapper. Forgejo checkout authentication and
host-side registry pull auth still exist. Effective token restriction on the
installed Forgejo version must be verified, not inferred from YAML. No production
Proxmox, Infisical or backend credentials are required or deliberately injected.

The upstream [workflow reference](https://forgejo.org/docs/latest/user/actions/reference/)
documents vars in job conditions. Forgejo's [runner security guidance](https://forgejo.org/docs/v15.0/admin/actions/security/)
also explains why allowed volumes are not confidential against workflow authors.
These references support the design, not proof of the installed server's policy.

## Next security action

The smallest remaining step is an operator-side authenticated review of CT301's
three registration scopes and who can schedule through each, including forks/PR
policy, plus effective job-token permissions. Do not retrieve secret values.
Confirm only trusted authors/workflows can use this daemon, then explicitly
accept the global rootful socket allowlist and potential LAN access for this
reviewed main-only validation. Exclusive push access here alone is insufficient.
If untrusted sources are admitted, keep the gate closed and separately authorize
restricting those sources; a second runner is not automatically required.

After that approval, publish the reviewed fix with the gate still closed. In
Homelab/homelab-iac Settings -> Actions -> Variables, set the repository variable
`CI_QUALITY_APPROVED` to the exact string `true` (not an Actions Secret). In
Actions -> Validate -> Run workflow, select `main` at the approved commit.
Changing the variable alone does not request a run. Verify the selected HEAD
before dispatch; subsequent main pushes will also run while the gate is true.
Record run URL, SHA and results before LIVE VERIFIED. The operator has since
executed run19; do not infer that its execution resolves the trust findings.
No extra infrastructure credentials are needed.

## Provider lock portability

Run19 failed in validate of pve-compute-forgejo-runner, after the workstation,
monitoring and migration roots. All seven roots pin bpg/proxmox0.112.0. Those
first three locks already had both platform h1 hashes; the historical runner,
Garage, tfstate and example locks had only darwin_arm64 h1, despite containing
all 14 signed ZIP hashes, including Linux AMD64. This was not a missing Linux
ZIP checksum or evidence of a modified official download.

The existing workflow creates fresh per-root TF_DATA_DIR directories and has
no provider mirror/shared plugin-cache configuration. Repository search found
no overrides; the local controller has no .terraformrc or TF cache/config env
overrides. The failed job's ambient CLI config was not independently captured.
The error's word "cached" also covers freshly installed unpacked providers;
it does not by itself establish a stale shared cache.

Terraform1.16.1 init can verify the ZIP using zh, but readonly prevents saving
the newly calculated platform h1. Subsequent validate verifies the unpacked
package against the lock; zh cannot verify an unpacked directory. See the
[exact provider check](https://github.com/hashicorp/terraform/blob/v1.16.1/internal/command/meta_providers.go)
and [hash implementation](https://github.com/hashicorp/terraform/blob/v1.16.1/internal/getproviders/hash.go).

Correction used the supported [providers lock command](https://developer.hashicorp.com/terraform/cli/commands/providers/lock)
for every root, preserving existing locks and versions:

```sh
terraform -chdir=terraform/stacks/pve-compute-forgejo-runner providers lock \
  -platform=darwin_arm64 -platform=linux_amd64
```

Apply that command per affected root after intentional provider changes, review
the diff, and retain init -lockfile=readonly in CI. Do not update locks in CI
to conceal an unexpected checksum mismatch. Terraform verified both packages
with provider signing key F0582AD6AE97C188 (registry-published, self-signed).
Only four missing Linux h1 entries changed; no hashes were removed or replaced.

Verified bpg/proxmox0.112.0 package hashes:

| Platform | Unpacked h1 | Archive SHA256 (already recorded) |
| --- | --- | --- |
| darwin_arm64 | njvcRZP07VIZLn4sUzVumOrquFuEot+Bv19OBo0iymQ= | 2f43edd19ea3454ed0dfa3c9bfbe7bfd4b97b2756ff37220c087ec95a6e7d21a |
| linux_amd64 | K8NuSgN6Yz3bm72phs75M4x46pQru2L+gSUs8mncCxM= | 1fa5fb40d2506db678b5f989d4929005680a187f6c91378ca5433fa490d9029b |

Both platform downloads were verified, not both platforms executed. No local
Linux engine is available (Docker Desktop socket absent); no CT301 container
was started for testing. Linux execution of the correction awaits Forgejo.

Correction validation: the unchanged workflow Terraform step passed on
darwin_arm64 with Terraform1.16.1: recursive fmt, seven fresh per-root init
(-backend=false -input=false -lockfile=readonly) and seven validate calls.
All seven locks retain the original version/constraints and 14 zh hashes.
check-quality.py passed (51 YAML, 6 Python, 18 shell checks), as did relative
documentation links and git diff --check. No plan/backend access was performed.
After operator review, push this fix to approved main with the existing gate;
inspect the new run, or manually dispatch Validate on that new main SHA. Do not
rerun the old f341450 job and expect it to contain the corrected locks.

## Commands and dependencies

The cloud-image VM example authorizes its `terraform` user with the tracked
`keys/doku-lab-admin.pub`, using
`file("${path.module}/../../../keys/doku-lab-admin.pub")`. This follows the
monitoring VM's existing admin-key convention and the operator's intended key.
Validation no longer needs an operator's `~/.ssh/id_ed25519.pub`; no private
key, CI variable or key generation is required. VM settings and username are
unchanged. Earlier validation on a personal controller did not demonstrate
independence from that controller's SSH files.
The corrected configuration passed the existing Terraform workflow step for
all seven roots with an empty temporary HOME on macOS ARM64 (Terraform1.16.1),
fresh per-root data directories, backend disabled and readonly lockfiles.
This is local validation, not a successful Forgejo run.

Job image stays ci-base:1.0.0 via homelab-iac label. Existing checksummed
Compose2.39.4 and CPython3.14.0 installers remain. Terraform1.16.1 now has a
pinned official SHA256. Gitleaks8.30.1 is reinstalled with pinned release SHA256
rather than trusting the image's binary. Digests came from vendor HTTPS release
manifests, not independently verified signatures. Mutable action/image tags and
transitive packages remain supply-chain limitations.

1. Full-history checkout; Gitleaks scans ancestors of HEAD, not ignored local
   files. Redaction enabled, all findings suppressed, failure exits nonzero with
   generic diagnostic. No report, state or plan artifact is uploaded.
2. Check HEAD whitespace; install controlled tools; rebuild .venv using existing
   setup-controller (the only Make target invoked).
3. Terraform fmt plus explicit six-stack AND example-root allowlist. Each root
   gets temporary TF_DATA_DIR and init -backend=false -input=false
   -lockfile=readonly before validate. Registry downloads verified against locks;
   no existing provider cache assumed. Download failure is a failure, not skip/PASS.
4. Thirteen playbook syntax checks using static inventory, Compose config,
   twenty synthetic runner cases and two mocked backup tests.
5. scripts/check-quality.py parses tracked YAML, compiles Python without executing
   it, runs bash -n on scripts/inline workflow commands and asserts trigger/gate,
   mount/credential exclusions, checkout settings and root/test coverage.
6. git diff --check for workspace whitespace after checks.

The historical example-provider blocker was resolved by explicit verified
installation, not exclusion. Fresh temporary init/validate succeeded locally
for all seven roots; no root backend, provider lock or active state changed.

Local commands using existing controller and matching Terraform:

```sh
terraform fmt -check -recursive terraform
.venv/bin/python scripts/check-quality.py
.venv/bin/python tests/runner-connections.py
.venv/bin/python tests/tfstate-backups.py
git diff --check
```

Use the workflow's exact syntax and per-root temporary-data init/validate loops
for equivalent coverage. Never substitute make *-plan or *-apply. Provider
installation needs registry access, not production credentials. For Gitleaks,
install the same version with the checksum for the controller platform; review
staged changes and rescan the final commit because git mode excludes uncommitted
work. Do not print findings into chat or public logs.

Local results: seven init/validate pairs, format, thirteen syntax checks, twenty
runner cases, two backup tests, YAML/Python/inline-shell guards, document links,
Gitleaks8.30.1 history scan and whitespace PASS. Existing Compose static check
retained but not rerun locally. Linux tool bootstrap and full Forgejo execution
NOT TESTED. Never run live Garage/PG qualification scripts here. No state migrated.
