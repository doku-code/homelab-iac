# 150-F - Prepare two independent Tailscale subnet routers

- Status: BLOCKED for live acceptance; repository phase LOCALLY VALIDATED.
- Permission: OFFLINE_CODE. No scans, live reads, apply, convergence, secret
  reads/writes, route approval, old-router retirement or Proxmox host changes.
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
