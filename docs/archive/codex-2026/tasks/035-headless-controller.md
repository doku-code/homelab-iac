# 035 - Headless Linux controller prerequisite

- Status: DEFERRED optional test adapter; capability retained, deployment unapproved.
- Dependencies: accepted030; portable050 selects its test environment independently.
- Scope: optional workstation hardware, isolated controller root, Ansible tool
  setup, mocked regression tests and validation-only CI. Not the LXC module 090.

## Acceptance

Reassessment 2026-09-25: [canonical architecture](../docs/architecture.md) makes
portable Mac/Linux recovery primary. This VM is useful but not required before
disposable K3s learning or synthetic kit tooling. Task100 adapts the headless
primitive for new cluster nodes without reusing this allocation implicitly.
The previous preflight below is preserved verbatim as evidence, not a current
instruction to proceed. VM603/.32 remain unapproved; no state or VM exists.
Resume this optional deployment only on a separately assigned task and its
original plan/apply/start/convergence gates. No acceptance claim is upgraded.

- Existing five workstation addresses, ordinary properties and lifecycle remain
  unchanged; GPU and four USB mappings remain defaults. Mocked regression proof.
- Separate headless root has no hostpci, USB, workstation tag or arbitration
  hook; no VMID/IP default. Invalid inputs fail. No host GPU preparation invoked.
- Controller software uses Ansible and repository dependency files; syntax
  checks need no production credentials. No Terraform application installation.
- All eight roots init backend-disabled/readonly and validate; mocked tests
  run without live states/providers. CI verdict tied to exact pushed SHA.
- Later live plan must confirm allocation, image provenance, storage, cloud-init
  and exclusive new-resource scope before separate deployment/start approval.

## Inspection 2026-09-25

Existing addresses: proxmox_virtual_environment_vm.workstation keyed by game,
dev, school, ubuntu, fedora. Live inventory confirms Ubuntu8101 template=true;
Fedora8200 template=false despite its name. No Debian cloud template verified.
Choose an explicitly checksummed cloud image rather than inherit unknown clone
hardware/identity. No image/allocation was selected or downloaded to Proxmox.
VM502 was running; no request to stop it or change host devices was made.

Operational procedure and proof limits: [headless controller](../docs/headless-controller.md).

Local evidence: eight roots passed backend-disabled readonly init/validate and
format; five mocked plan cases passed, including immutable baseline guards for
ordinary workstation configuration. New Ansible syntax passed (no host in the
static inventory, intentionally no live allocation). Live no-op/deployment and
guest tool installation remain NOT TESTED. Forgejo API run135 (UI run24)
passed for exact commit 8c12871aa0d5e31c55162a4a84e5c4fcd86837aa on 2026-09-25:
https://git.doku-lab.net/Homelab/homelab-iac/actions/runs/24.
This is Linux AMD64 repository validation, not guest provisioning evidence.
Operator review of the deployment procedure remains required; no live plan is
claimed and no acceptance criterion is weakened by the CI result.

## Deployment preflight, gate 1 - 2026-09-25

Read-only cluster inventory, pve-lab status/storage/network/DNS and declared
guest IP configuration inspected. A candidate VMID is absent cluster-wide;
proposed allocation is in ignored controller terraform.tfvars, marked UNAPPROVED.
No controller state/plan created, image downloaded to Proxmox, or VM started.

- pve-lab: 16 cores/32 threads, approximately 27.5 GiB available RAM. Workstations
  were already stopped at inspection; none was stopped by this task. Capacity
  accommodates the proposed 2-vCPU/4-GiB controller plus one 16-GiB workstation.
- vmbr0 active with the existing gateway and DNS. local supports import and
  has about 16.6 GiB available; lab-vms supports images and has about 1.27 TiB
  available. No storage reconfiguration required by the proposed profile.
- Candidate IP absent from declared guest network/cloud-init configuration,
  pve-lab neighbor cache and AdGuard candidate rewrites; forward/reverse DNS
  returned NXDOMAIN. These are NOT proof of availability: guest-internal static
  settings and router leases/reservations remain unverified. AdGuard DHCP is
  disabled. Operator must confirm the candidate against router DHCP range,
  leases/reservations and independently assigned static addresses before plan.
- Official Debian generic AMD64 qcow2 build 20260914-2601 streamed on the
  controller only, matched official SHA512SUMS (HTTPS Debian origin); derived
  SHA256 recorded in private inputs. Upstream publishes SHA512, not SHA256 in
  this listing. No detached signature verified; do not claim one. No image
  file retained or imported. The generic image avoids unknown clone hardware.
- Tracked admin public-key fingerprint matches the key accepted by existing
  authenticated pve-lab SSH. No private key copied or manually read.
- Existing workstation API endpoint/TLS convention reused in proposed inputs;
  controller provider receives proxmox_insecure explicitly. Universal Auth
  runtime pair unavailable here: after gate 1 the existing authenticated operator
  shell may need to run the exact documented controller-plan command.

Expected scope is two new resources only: proxmox_download_file.linux and
proxmox_virtual_environment_vm.controller in pve-lab-controller's isolated local
root. This is an expectation, NOT a Terraform plan result. PCI/USB/hook absent;
started/on_boot/reboot_after_update false; prevent_destroy retained.

Next gate: confirm the candidate IP is free and excluded from dynamic allocation,
then explicitly approve `make controller-plan CONTROLLER_ALLOCATION_REVIEWED=yes`.
Apply, start and Ansible convergence each remain separately gated. Guest readiness
and all live acceptance remain NOT TESTED. No production kit material involved.
