# 035 - Headless Linux controller prerequisite

- Status: IN_PROGRESS; capability validated locally and in CI; operator procedure review pending, no deployment authorized.
- Dependencies: accepted 030; precedes the disposable VM test in 040.
- Scope: optional workstation hardware, isolated controller root, Ansible tool
  setup, mocked regression tests and validation-only CI. Not the LXC module 090.

## Acceptance

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
