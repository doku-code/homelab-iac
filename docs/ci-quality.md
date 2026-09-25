# Initial CI quality gate

Status: **LOCALLY VALIDATED; LIVE EXECUTION BLOCKED pending task 010 approval**.
No Forgejo job triggered, live variable/permission changed or push performed.
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
Record run URL, SHA and results before LIVE VERIFIED. No push, variable change
or dispatch was performed. No extra infrastructure credentials are needed.

## Commands and dependencies

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
