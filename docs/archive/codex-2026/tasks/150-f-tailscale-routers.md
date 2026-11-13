# 150-F - Prepare two independent Tailscale subnet routers

- Status: BLOCKED for live acceptance; repository phase LOCALLY VALIDATED.
- Permission: operator-authorized verified SSH enrollment and guest convergence
  on existing CT306/307, plus targeted read-only checks and repository changes.
  No further Terraform operations, route approval, old-router retirement,
  Proxmox host changes or push are authorized in this session.
- Parent: [150](150-pve-infra-evacuation.md), independent of the K3s/Flux path.
- Operator target: ts-router-01 on pve-k8s-01 and ts-router-02 on pve-k8s-02,
  SAME existing tailnet, exact 192.168.0.0/24, separate persistent identities.
- Authoritative implementation/procedure: [router runbook](../docs/tailscale-routers.md).

## Acceptance

- [x] Terraform models only two unprivileged, onboot, TUN-enabled Debian CTs;
  missing/duplicate allocations rejected in offline mocked tests.
- [x] Ansible models pinned official package/trust, forwarding and identity
  preservation; first-registration-only runtime secret reads, no guest key file.
- [x] Offline syntax, regression, format, provider validation and quality checks
  pass; staged diff contains no secrets/state/unrelated changes.
- [x] Plan/apply/converge, manual approvals, failover/rollback and distinct PBS
  identity handling documented without live-success claims.
- [ ] Operator supplies two free VMIDs, two free LAN IPs and confirms local
  storage/template/bridge/capacity, provider device permissions and SSH trust.
- [ ] Separately approved live deployment, existing-tailnet membership,
  distinct identities, exact route preferences, second convergence and remote
  new-pair failover qualified; PBS coverage checked.
- [ ] Old host Tailscale retirement explicitly approved/verified; parent150
  cluster removal remains separate. No automatic next task.

## Evidence - 2026-09-29

Initial worktree clean at e862168. Inspected CT roots, only existing headless VM
module, inventory, Make/Infisical/CI and Task150 inventory. Repository does not prove
two unused allocations or the newly supplied nodes' storage. No values guessed.
Only public upstream metadata was consulted: provider 0.112.0 devN API,
Tailscale trixie package 1.102.4 and signing-key SHA256. Existing infra preferences
are operator-provided evidence, not new live inspection. Full live checklist
remains open. No real Infisical secret or private Tailscale state was accessed.

Local checks passed on macOS ARM64:

- `make tailscale-check`: four mocked Terraform cases, invalid/duplicate
  allocation rejection, conditional registration, missing-key/no-log/stdin
  checks, preference drift/idempotence, denied approvals and real Ansible
  parsing of a synthetic Make-generated inventory. No real guest execution.
- Terraform recursive format and all TEN roots initialized with backend disabled,
  input disabled, readonly lockfiles and temporary provider directories; validate
  passed. New lock obtained via official registry for darwin_arm64/linux_amd64,
  signed provider 0.112.0; Linux execution and live plan NOT claimed.
- All playbooks syntax-checked; absent generated inventory groups produce the
  expected warnings, not a live connection. `ansible-lint` is not installed.
- Existing runner, logical-backup, VM profile, Recovery Kit, Stage A, explicit
  inputs, K3s and Flux offline regression suites passed.
- Quality parser: 71 YAML, 16 Python, 25 shell checks; 115 relative documentation
  links in changed Markdown files; whitespace and staged credential/path checks.
- Gitleaks 8.30.1 staged-source scan passed with redaction; ignored secrets,
  states and private inputs were not included.

No push: AGENTS requires explicit per-task authorization. No remote CI or live
success claimed. Next operator action: supply two confirmed VMIDs/IPs and the
node-local prerequisites in the runbook, review the code, then separately approve
plan/deployment and cutover. Parent150 and Task120 remain untouched operationally.

## Approved allocation and plan attempt - 2026-09-29

The operator subsequently approved ts-router-01 = VMID306 /192.168.0.36/24 on
pve-k8s-01, ts-router-02 = VMID307 /192.168.0.37/24 on pve-k8s-02, vmbr0,
gateway192.168.0.1 and the existing
`pve_library:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst` template.
The ignored root-local `terraform.tfvars` now contains these allocations.

Targeted read-only evidence through strict-verified SSH to pve-core and `pvesh`:

- CT201 on pve-k8s-01: `local-lvm:vm-201-disk-0,size=8G`.
- CT200 on pve-k8s-02: `local-lvm:vm-200-disk-0,size=8G`.
- Both local-lvm stores active/enabled, type lvmthin; available bytes respectively
  146471554909 and145286373363. The new CTs therefore use local-lvm, not a new
  storage convention. The exact template is present on both nodes.
- Cluster inventory contains neither306 nor307. IP availability is the operator's
  allocation decision, not an independently performed scan.
- Direct SSH to .16 lacked a known key and was refused; no key was enrolled or
  checking disabled. Existing trusted pve-core access supplied the API reads.
- Local API TLS verification cannot find the issuer. Private inputs explicitly
  use `proxmox_insecure=true`, matching the existing pve-core-tfstate convention;
  no global TLS default, certificate or Proxmox configuration was changed.

`make tailscale-check` passed again (four mock cases, inventory parsing,
secret/idempotence/approval tests and Ansible syntax). Quality parser passed.
`make tailscale-plan` passed fmt, init and validate but STOPPED at the Universal
Auth guard: neither INFISICAL_CLIENT_ID nor INFISICAL_CLIENT_SECRET is available
to this execution environment. No saved plan exists; no real plan counts or
provider create/change/destroy result can be claimed. No apply or guest mutation.

Next action from the authenticated operator shell: `make tailscale-plan`, then
review the saved plan. Expected configuration is exactly two new containers,
zero existing-resource changes/deletions; that expectation is NOT a reviewed
live plan. Deployment and cutover still require separate approval.

## Root-only API correction after operator apply failure

The operator reports Proxmox rejected device passthrough because it requires
`root@pam` password authentication. Current live existence of306/307 is NOT
assumed; operator verification remains required. No import, state deletion,
live query or apply is part of this correction.

The two router instances now use `proxmox.root`, with explicit root@pam username
and empty API token. Existing default provider and other roots are unchanged.
The Tailscale-only Universal Auth runtime reads `/proxmox/PROXMOX_ROOT_PASSWORD`
in dev, maps it to provider environment (not Terraform inputs), strips competing
auth, blocks logging/CLI overrides and rejects old-provider saved plans on apply.
No infrastructure attributes or private allocation values were changed.

Validation: format, readonly init and validate passed; four Terraform mock cases,
seven synthetic auth tests (password environment, no fallback, no competing
token/ticket, no credential argv, log guards, apply approval, old-plan rejection,
sanitized SDK failure), existing router tests and Ansible syntax passed.
Repository quality parsing (71 YAML,18 Python,25 shell), documentation links,
staged Gitleaks scan and whitespace checks passed. Stage A's existing input
regressions also passed. CLI help confirms path scoping and disabled expansion/
imports; no real password was fetched. Ansible-lint remains unavailable.

The NEW `make tailscale-plan` attempt invalidated the old saved plan, passed init
and validate, then stopped because Universal Auth credentials are still absent
in this execution environment. No replacement plan exists and no live plan
counts can be claimed. Expected 2 add /0 change /0 destroy remains conditional
on the operator's post-failure live-state verification and new plan review.
Run `make tailscale-plan` from the authenticated shell with access to the new
Infisical secret; do not export the password manually or apply the old plan.
This does not authorize TUN removal, privileged containers or apply.

## SSH enrollment and partial convergence - 2026-09-30

The operator reports successful apply: **2 added, 0 changed, 0 destroyed**.
CT306/.36 and CT307/.37 exist; no apply, import or state modification was repeated.
Public ED25519 keys were read inside each CT through `pct exec` on its owner,
via already trusted pve-core SSH and each owner's cluster-managed SSH trust file.
Strict checking remained enabled on every hop. Complete key bytes matched the
network-presented ED25519 keys. No conflicting controller trust entry existed;
both verified keys were appended to the operator's normal known_hosts:

- ts-router-01 /192.168.0.36: `SHA256:CHrz7moXviWKlcxbPviXNex/HwMNfUI0JWe0xPuAPpI`.
- ts-router-02 /192.168.0.37: `SHA256:IdpuTu7WMyqi6ldU4NwqO8Fy/DjNN87tSFhejAMYzqM`.

Subsequent strict SSH confirmed both expected hostnames. Approved
`make tailscale-configure TAILSCALE_CONFIGURE_APPROVED=yes` reached CT306:
**ok=15 changed=5 unreachable=0 failed=1**. It stopped at the first-registration
Universal Auth credential assertion. Both INFISICAL_CLIENT_ID and
INFISICAL_CLIENT_SECRET are absent in this agent environment (presence-only
check). No Infisical read or Tailscale registration was attempted. Serial execution
correctly prevented advancing to CT307 after the failure.

Read-only post-attempt observations:

| Check | ts-router-01 | ts-router-02 |
| --- | --- | --- |
| Strict SSH / hostname | verified | verified |
| TUN character device | present | present |
| IPv4 forwarding | 1 | 0 |
| tailscaled | active | inactive; package absent |
| Tailscale version / backend | 1.102.4 / NeedsLogin | not installed |
| Tailnet ID/IP / advertised routes | none / none | unavailable |

CT306 preferences have RouteAll=false, RunSSH=false, NoSNAT=false and no exit
node. CorpDNS is still the pre-registration default true; intended preferences
have NOT yet been applied. Device presence alone is not proof of functional TUN
or subnet routing. Distinct registered identities, existing-tailnet membership,
exact route advertisements and second convergence remain unverified.

Next action: run `make tailscale-configure TAILSCALE_CONFIGURE_APPROVED=yes`
from the existing authenticated operator shell. No admin-console approval is
required yet: neither router was registered in this attempt. Once registered,
follow the runbook's device-approval gate (if requested) and approve ONLY
192.168.0.0/24 for both new routers, never exit routes. Do not retire pve-infra.
No old device/service, private key, Terraform state or container isolation was
changed. Task remains BLOCKED for live acceptance, not complete.

Repository validation after this documentation update: `make tailscale-check`
passed (seven synthetic authentication tests, four mocked Terraform cases,
router guard/idempotence checks and Ansible syntax). Quality parsing passed
(71 YAML, 18 Python, 25 shell); six relative documentation links and
`git diff --check` passed. No infrastructure plan/apply or remote CI was run.
