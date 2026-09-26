# 100 - Reusable headless VMs for Stage A

- Status: repository-only phase COMPLETE and CI VERIFIED; full task BLOCKED
  at separately authorized live preflight/acceptance. No live gate is satisfied.
- Depends on: reviewed target architecture and explicit task assignment; existing
  035 capability, provider locks and workstation-preservation tests.
- Permission: OFFLINE_CODE, commit/push and quality CI explicitly authorized;
  no live allocation, provider plan, apply, start or convergence authorized.
- Deliverable: three-node environment profile and reusable headless VM primitive,
  not an operational Kubernetes cluster. Full production kit is not a dependency.

## Implementation scope

Inspect pve-lab-controller main/variables/tests, tests/vm-profiles.py, controller
playbook, Makefile and validate.yml. Reuse the minimal ordinary VM properties;
do not duplicate the workstation stack. A small internal headless module is now
justified by standalone-controller and three-node consumers. Determine resource
addresses before editing. Never move workstation or other stateful-root addresses.
The undeployed controller root may adopt the component only after confirming
it still has no state/resources; stop if this has changed.

Implementation decision: the controller root is left unchanged. No local state
or plan exists, but this repository-only phase does not establish live absence.
The new module is shared by three Stage A instances; no existing address moves.

Propose a separate Stage A root/state with map keys server-1/server-2/server-3,
explicit unique VMIDs/IPs/hostnames, per-node placement/storage/sizing and one
checksummed image per node/datastore where needed. Node system/cloud-init disks
must be local, not the TrueNAS library. Environment inputs, not module code,
select hosts; no default live allocation. No GPU/USB/hook/workstation tags,
host role, automatic start or host-wide shutdown. Preserve destruction protection.

Reuse OS prerequisites through a narrowly scoped Ansible baseline, without
installing full controller tooling on K3s nodes. Inventory derives from reviewed
outputs or the same allocation map, not independently maintained conflicting IPs.
Make interfaces must distinguish static check, reviewed plan, exact saved apply
and later start/configure; discard stale saved plans before a newly authorized
plan and never auto-apply on failure. No Infisical credentials in offline tests.
Keep node bootstrap state operator-local with one writer and ignored private
inputs. K3s installation and tokens belong to110, not Terraform cloud-init.

## Tests and acceptance

1. Mocked rendering proves exactly three unique headless nodes and expected
   image count; no passthrough/hook/arbitration or automatic start.
2. Duplicate VMID/IP/name, missing allocation/checksum, incompatible storage
   intent and undersized inputs fail clearly. Test alternate placement map
   without changing component code or creating resources.
3. Existing workstation preservation tests remain unchanged in strength;
   no address/identity/disk/lifecycle drift introduced to existing roots.
4. Every root passes fmt, readonly/backend-disabled init/validate; relevant
   Ansible syntax/render, YAML/shell checks and CI for exact pushed SHA pass.
5. Explicit resource-owner/state and allocation-to-inventory contracts documented.
   Static PASS does not complete live acceptance below.

## Subsequent live gates (not approved)

- Preflight: fresh cluster VMIDs, DHCP/static IP proof, CIDR/bridge/storage,
  local SSD capacity, public image provenance and SSH trust. Operator dedicates
  pve-lab to the lab; workstations remain powered off, all configuration/state
  preserved. Measure host overhead and proposed 12-GiB cluster (3 x 4 GiB)
  against 32-GB physical capacity; retain at least 2-GiB safety headroom beyond
  host overhead. Do not alter workstation power/configuration. No reuse of603/.32
  without separate review; standalone controller remains optional/separate.
- Approve exact allocations and new-resource-only plan; inspect no existing
  resource changes, no state moves/imports. Save reviewed plan with identity.
- Separate exact-plan apply approval; creation stopped. Then explicit start
  and OS baseline approval, trusted SSH identity check and second convergence.
- Live acceptance: three distinct accessible Debian nodes, expected local disks,
  no passthrough/hook; workstation configuration/state unchanged and still off.

Rollback: before apply, abandon proposed code/profile without touching existing
states. After creation, keep nodes stopped on failure; deletion requires a new
reviewed plan and explicit destruction approval, never automatic prevent_destroy
removal. Preserve state/evidence. Close only with operator acceptance and precise
static/live results. Next: assign110; do not install K3s automatically.

## Repository-only evidence - 2026-09-25

- Shared module and separate `pve-lab-k3s` root implemented; proposal is three
  2-vCPU/4-GiB/32-GiB nodes with no VMID/IP defaults. One image per node/datastore.
- Applied-output inventory, minimal OS baseline, separate guarded plan/exact-hash
  apply/start/configure interfaces. No K3s or controller toolchain on lab guests.
- `make stage-a-check` PASS: 15 mocked VM cases (3 unchanged workstation,
  2 unchanged controller, 10 new Stage A), baseline rendering, denied gates,
  Make dry-runs and stale/partial-plan removal through stubbed commands.
- All nine roots: code-only copies, isolated HOME, readonly/backend-disabled
  init and validate PASS on macOS ARM64. Provider version/checksums unchanged;
  new lock copied from the already-qualified identical controller dependency.
- All 16 playbooks syntax PASS; absent `k3s_lab` hosts are expected until apply.
  Terraform fmt and git diff whitespace PASS. Existing workstation/controller
  roots and workstation roles are byte-for-byte unchanged against dcbc83a.
- Forgejo [run 27](https://git.doku-lab.net/Homelab/homelab-iac/actions/runs/27)
  (API ID138) PASS on CT301/Linux AMD64 for implementation commit
  `ce61e8689867855489322aeac76d12d5844ad9f4`; all nine roots and remaining quality
  checks passed. GitHub main independently matched that full SHA. This is
  repository CI, not provider planning, recovery or runner isolation proof.
- No private inputs, new state or live allocation created. Six existing
  authorities remain unchanged; no live infrastructure action performed.

Next gate is separately authorized read-only allocation/capacity/trust preflight,
not Task 110 installation. Full Task 100 remains open until live criteria and
operator acceptance; the repository-only phase does not authorize those actions.
