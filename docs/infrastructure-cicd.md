# Infrastructure CI/CD Safety Gates

## State audit: 2026-09-21

Repository-only audit; no provider refresh, plan, state migration, or live action.
The operator reports all three CT301 workload smoke tests green and CT300 off.
These observations do not mean the powered-off CT300 has left Terraform state.

Every root under terraform/stacks has no backend/cloud block and uses the
implicit local backend. Each has an ignored terraform.tfstate and terraform.tfvars.
There is no .terraform backend metadata, workspace selector, or workspace state
directory in these roots. No configured remote state service was found.

| Stack | Local state relative to repository | Managed instances | Status |
| --- | --- | --- | --- |
| deb13-monitoring | terraform/stacks/deb13-monitoring/terraform.tfstate | 2 | Monitoring VM and cloud-image download |
| pve-lab-workstations | terraform/stacks/pve-lab-workstations/terraform.tfstate | 5 | Workstation VMs; high-impact hardware/passthrough |
| pve-compute-forgejo-runner-migration | terraform/stacks/pve-compute-forgejo-runner-migration/terraform.tfstate | 1 | CT301, serving all three runner connections |
| pve-compute-forgejo-runner | terraform/stacks/pve-compute-forgejo-runner/terraform.tfstate | 1 | CT300, powered off but still managed; retirement only |

These files are the state used by the repository's operator workflows, not a
remote copy available to CT301. All report Terraform 1.16.1 and have state lineage.
Only structural metadata/counts were inspected for the audit; no state values
or credentials were printed. No live inventory reconciliation was performed.
terraform/examples/cloud-image-vm is an example, not an active deployment root.

Local locking protects a local file on that filesystem, not independent Mac/CI
copies. A fresh Actions checkout has neither the state nor the private tfvars.
Missing variables may stop a plan, but supplying them would still leave an empty
state: that is NOT a production plan. CI planning is unsafe for every root today.
Do not copy state to Git, the runner, or Actions artifacts as a workaround.
See [Terraform local backend](https://developer.hashicorp.com/terraform/language/backend/local).

## What is enabled now

validate.yml runs on push and pull_request, using label homelab-iac and its
ci-base:1.0.0 mapping, without a container/socket override or infrastructure secrets.
Checkout authentication is not persisted. Existing Compose 2.39.4, Terraform
1.16.1, standalone CPython 3.14.0, and controller requirements remain unchanged.
The existing setup is reused for offline runner regression tests, not duplicated.

Terraform validation uses init -backend=false -input=false -lockfile=readonly
and validate, never plan. The explicit validation allowlist remains:

- pve-lab-workstations
- deb13-monitoring
- pve-compute-forgejo-runner-migration

The CT300 root is audited and checked locally but excluded from normal CI stack
selection. The recursive formatting check still covers tracked Terraform files.
No dynamic path input, changed-stack discovery, plan workflow, or apply scaffold
is introduced. The eventual plan allowlist should start with the same three roots,
enabling each only after its own state/input/credential gates pass.

There is NO automatic path from push, PR, or schedule to terraform apply.
publish-ci-base.yml remains a separate manual image-publishing workflow, not CD.
Its explicit privileged socket and package-write credentials are not available
to the ordinary validation job. Existing local Make apply targets still mutate
when deliberately invoked; runner-migration-apply includes -auto-approve and
must never be reused as an unattended CI step.

## Recommended remote state architecture (proposal only)

Prefer one managed AWS S3 bucket, not a new service hosted on the runner or a
cluster whose repair depends on that same state. This introduces a cloud-account,
billing, and credential dependency requiring operator approval, but no new
homelab daemon/database. No existing S3 service/account is assumed available.
If off-site managed storage is unacceptable, evaluate an existing independent
S3-compatible service separately, including conditional-write locking and restore
tests; do not assume API compatibility is enough or silently deploy one.

Use one stable key per stack, only the default workspace:

- homelab/deb13-monitoring/terraform.tfstate
- homelab/pve-lab-workstations/terraform.tfstate
- homelab/pve-compute-forgejo-runner-migration/terraform.tfstate
- homelab/pve-compute-forgejo-runner/terraform.tfstate (CT300 only if still retained)

Enable bucket versioning, default server-side encryption, public-access blocking,
TLS-only access, and native S3 locking via use_lockfile = true. No DynamoDB is
needed. Keep state access narrow by key/prefix; no public/shared artifact links.
Normal clients do not need state-object delete permission. Lock files need
GetObject/PutObject/DeleteObject; state access needs GetObject and, for migration
and apply, PutObject, plus appropriately restricted ListBucket. An explicitly
tested planning identity may omit state writes but must still acquire/release
locks. Never use -lock=false. See the
[S3 backend permissions](https://developer.hashicorp.com/terraform/language/backend/s3).

Versioning is recovery history, not an independent backup. Retain encrypted
off-account/offline snapshots under operator control and test restoration into
an isolated key. Keep recovery access independent of CT301 and document ownership,
retention, and break-glass access. Never restore over a live key while clients run.

## Exact migration sequence for later approval

Do not execute these steps as part of this repository-only milestone. Bucket
name, region, access policy, and backup destination require approval first.
Do one stack at a time; do not combine this with CT301 renaming or resource changes.

1. Freeze Terraform use from every operator and CI. Confirm the current operator
   checkout is authoritative, default workspace is in use, and no TF_WORKSPACE,
   TF_DATA_DIR, or TF_CLI_ARGS override redirects it. Reconcile any external state
   copies privately. Record state lineage, serial, managed instance addresses,
   Terraform/provider versions, and checksums without publishing attributes.
2. Back up each original state, backup state, private tfvars, and provider lockfile
   to approved encrypted storage. Verify backups are readable. Secure missing
   input sources: endpoint/tls settings for all roots, CT301 management public key,
   and the CT300 adoption fields if that root is retained. Promote reviewed
   non-secret inputs to tracked configuration or Forgejo variables; keep sensitive
   inputs in the intended Infisical project. Do not assume CI has the Mac tfvars.
3. Provision the approved bucket/policy/versioning/encryption/backup configuration
   out of band under separate approval. Confirm its independence from CT301 and
   test backend locking with a disposable key, not production state. Existing
   Infisical Universal Auth may deliver approved backend credentials at runtime;
   no credentials belong in backend HCL, Git, logs, or cached runner files.
4. In each root add and review backend.tf containing a literal S3 backend with
   approved bucket/region, that root's exact key, encrypt = true, and
   use_lockfile = true. Keep these non-secret metadata in Git. Do not add backend
   blocks during this milestone. Verify the destination key is absent; if it
   exists, STOP and reconcile lineage, never overwrite it blindly.
5. From the original operator checkout, with approved backend credentials in the
   runtime environment, run the one applicable command interactively:

   ```sh
   terraform -chdir=terraform/stacks/deb13-monitoring init -migrate-state -lock-timeout=5m
   terraform -chdir=terraform/stacks/pve-lab-workstations init -migrate-state -lock-timeout=5m
   terraform -chdir=terraform/stacks/pve-compute-forgejo-runner-migration init -migrate-state -lock-timeout=5m
   # Only if CT300 state still needs migration before its separately approved retirement:
   terraform -chdir=terraform/stacks/pve-compute-forgejo-runner init -migrate-state -lock-timeout=5m
   ```

   Review Terraform's source/destination prompt before accepting. Do not use
   -force-copy, -reconfigure, or a fresh empty checkout for this transfer.
   This migrates storage, not resource identity. It does not approve an apply.
6. Privately compare the migrated state with the encrypted original: lineage,
   resources/instance IDs, attributes, and any explained serial change. Never
   print state pull output in CI. Verify the expected S3 key/version and lock
   behavior. A fresh credentialed checkout must read the same lineage and must
   fail closed if the approved state object is missing or access is denied.
7. With matching inputs and provider credentials, perform a protected operator
   plan using -input=false -lock-timeout=5m -detailed-exitcode. Handle 0 (no diff),
   2 (diff), and all other codes (failure) distinctly. Migration itself should
   cause no resource changes; investigate recreation or unexpected drift. CT300
   power state may differ from its old desired configuration: never apply it
   just to reconcile the audit. Do not upload raw output or binary plans.
8. Verify restore procedures and backup retention before lifting the freeze.
   Archive leftover local state outside the active checkout as recovery-only;
   all clients must use the reviewed remote backend, never an old local fallback.
   Do not remove the recovery copy or merge states. On failure, freeze both sides,
   compare state generations, and choose one authoritative copy under explicit
   recovery approval; never resume both local and remote writers.

The backend's identity/lineage check must be part of the later CI gate; a backend
block alone does not prove that a nonempty correct production object exists.
Document the expected lineage privately, and treat resource-count checks alone
as insufficient. Backend migration and rollback are separate approved operations.

## Credentials and trust before enabling plans

| Category | Consumer and boundary |
| --- | --- |
| Runner connection UUID/token pairs | Runner daemon only, Homelab-IaC Infisical /forgejo-runner/connections; not workflow provider authentication |
| Registry read credential | Runner private-image pulls; no Proxmox/backend access |
| Registry publish credential | Manual image workflow only; not infrastructure CD |
| INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET | Repository Actions Secrets, Universal Auth to the project from .infisical.json; no human Infisical session |
| Proxmox workload credential | Runtime provider environment, e.g. bpg PROXMOX_VE_API_TOKEN; scoped to relevant nodes/resources and required API operations |
| Backend credential | Runtime S3 access under the separate policy above; capability not currently established |

Existing INFISICAL_RUN supplies the project/env to infisical run, then invokes
Terraform. Provider blocks specify endpoint/TLS but no literal authentication.
Actual exported Proxmox credential names/ACLs have not been inspected. Ansible's
PROXMOX_URL/USER/TOKEN_ID/TOKEN_SECRET convention is not automatically bpg's
provider authentication. Confirm that the existing identity can read only the
needed provider/backend paths; do not export every workload secret into plan CI.
Reuse an existing identity where its trust and ACLs fit; report missing read-only
Proxmox audit/VM/datastore/network capabilities before creating credentials.
Apply may additionally require resource write privileges and any provider-required
SSH operations. Exact ACL sufficiency must be tested later against the chosen
operations. No credentials were read or created in this audit.

State read access itself exposes sensitive infrastructure data. A Terraform plan
can run providers, data sources, and repository-controlled code. Do not give PR
code production secrets/state merely because the command is called plan. For
untrusted PRs/forks use validation only. Automatic plans on trusted PR revisions
or main are a later opt-in after review of who may change that code, workflow
protection, and state/log access. Labels are scheduling, not security boundaries.

Later plan jobs must use the explicit stack allowlist, fixed paths, protected
credential scope, readonly provider lockfiles, backend/lineage preflight, default
workspace, -input=false, -lock-timeout=5m, and detailed exit codes. Publish only
an allowlisted summary (stack/ref and add/change/destroy counts), not raw plan JSON,
stdout, state, or binary artifacts. Sensitive flags are not a complete redaction
policy. Review full plans privately; command failures can also expose values.

Manual apply is NOT implemented. Initially keep operator-local apply against
the shared backend: review a newly created protected plan, then explicitly apply
that exact local saved plan before removing it. For later Forgejo dispatch require
main, immutable commit verification, fixed stack choices, explicit confirmation,
locking, and a protected re-plan. Dispatch followed by re-plan/apply is not approval
of a previously reviewed exact plan. Do not claim Forgejo environment approval
features or safe cross-job artifact handling without verifying them first.

## Ansible and final runner cleanup

Only Ansible syntax and offline runner tests are automated here. Convergence
remains deliberate operator Make commands. Future manual jobs must bind a known
playbook, inventory, and narrow host set; never accept arbitrary command/path/host.

For a later separately approved maintenance step:

1. Preserve CT300 backups and its authoritative state while it is powered off.
   Review old runner-import/runner-live-plan/runner-bootstrap-access and CT300
   inventory/bootstrap files as retirement-only; do not run them against CT301.
2. Verify all three workloads remain green, then explicitly retire old Forgejo
   registrations and CT300. Review its prevent_destroy guard and targeted root
   destruction plan, not state rm to hide a live CT. Do not apply old start intent.
3. Archive the emptied CT300 state/root and backups. Only then canonicalize the
   CT301 directory, Make names, ansible inventories/playbooks and --limit alias.
   Keep VMID 301/IP unchanged. Prefer retaining the stable remote state key and
   resource address; a path rename is not a resource rename. If resource address
   changes are desired, review moved blocks separately to prevent recreation.
4. Rename hostname/tags only in a separate reviewed maintenance plan. Update
   runner-migration-* Make targets and documentation after the identity transition.
   Never move CT301 over CT300 state or combine backend migration with this step.

docs/forgejo-runner.md contains earlier bootstrap/registration procedures, now
completed according to the operator; do not rerun publication or replace identities
as part of CD setup. Historical documentation remains historical.
