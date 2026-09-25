# 100 - Reusable headless VMs for Stage A

- Status: PLANNED; first code-only implementation after architecture approval.
- Depends on: reviewed target architecture and explicit task assignment; existing
  035 capability, provider locks and workstation-preservation tests.
- Permission: future OFFLINE_CODE first; this task file authorizes no execution.
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
  local SSD capacity, public image provenance and SSH trust. Measure running
  workstation + host baseline and proposed 9-GiB cluster; retain 2-GiB host
  margin. No workload shutdown to manufacture headroom. No reuse of603/.32
  without separate review; standalone controller remains optional/separate.
- Approve exact allocations and new-resource-only plan; inspect no existing
  resource changes, no state moves/imports. Save reviewed plan with identity.
- Separate exact-plan apply approval; creation stopped. Then explicit start
  and OS baseline approval, trusted SSH identity check and second convergence.
- Live acceptance: three distinct accessible Debian nodes, expected local disks,
  no passthrough/hook; workstation remains usable, no unintended changes.

Rollback: before apply, abandon proposed code/profile without touching existing
states. After creation, keep nodes stopped on failure; deletion requires a new
reviewed plan and explicit destruction approval, never automatic prevent_destroy
removal. Preserve state/evidence. Close only with operator acceptance and precise
static/live results. Next: assign110; do not install K3s automatically.
