# 100 - Reusable headless VMs for Stage A

- Status: DONE / LIVE VERIFIED 2026-09-26; operator explicitly accepted the
  technical evidence and authorized formal closure before assigning Task110.
- Depends on: reviewed target architecture and explicit task assignment; existing
  035 capability, provider locks and workstation-preservation tests.
- Permission: operator completed approved apply/start; limited guest TOFU and
  Debian baseline authorized and completed. Documentation commit/push/CI allowed.
  No further Terraform/Proxmox changes or Task110 installation authorized.
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

## Live gates (completed evidence below; not standing authorization)

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
- Follow-up loader regression: temporary generated inventory must have a `.json`
  suffix, not `mktemp`'s random extension. Added a real offline
  `ansible-inventory --list` test for all three hosts and allocation variables.
  The run 27 evidence above predates this narrowly scoped loader correction;
  its exact pushed CI result is reported separately.

Next gate is separately authorized read-only allocation/capacity/trust preflight,
not Task 110 installation. Full Task 100 remains open until live criteria and
operator acceptance; the repository-only phase does not authorize those actions.

## Read-only live preflight - 2026-09-25

Repository at `684611971940595c50d5a1ad56eb4a272367ddff`; its final loader fix
passed Forgejo run29 (API140). This preflight did not execute Terraform or Ansible.
Only targeted SSH reads, DNS/three ICMP probes, router entry-point GET and official
image streaming were performed. No workstation or host configuration changed.

### Historical candidate, superseded and discarded on 2026-09-26

The following 701-703 proposal is retained only as preflight history. Do not use
it in inputs or commands. The approved allocation below replaces it.

| Key | VMID | Hostname | Proposed IPv4 |
| --- | --- | --- | --- |
| server-1 | 701 | k3s-lab-1 | 192.168.0.33/24 |
| server-2 | 702 | k3s-lab-2 | 192.168.0.34/24 |
| server-3 | 703 | k3s-lab-3 | 192.168.0.35/24 |

All on pve-lab: 2 vCPU, 4096 MiB RAM, 32 GiB disk each; vmbr0,
gateway 192.168.0.1, DNS 192.168.0.20, image datastore local, disk/cloud-init
datastore lab-vms. Task035's VM603/.32 remain separately unapproved and unused.
No private Stage A inputs, state or saved plan have been created.

### Observed evidence

- Cluster inventory: 701/702/703 and proposed hostnames absent. No pve-lab guest
  running; workstations 501/502/503/601/602 already stopped. Read only; no power
  or mapping changes. Absence does not reserve the VMIDs; recheck before plan.
- pve-lab: 16 physical cores/32 threads, 29.98 GiB OS-visible RAM from the
  operator's 32-GB host, 27.54 GiB available, about 2.45 GiB used; load averages
  0.00 and no swap used. Proposed 12 GiB leaves about 15.54 GiB of observed
  available memory before additional VM overhead: adequate for a 2-GiB safety
  reserve. Snapshot, not a performance/peak-capacity qualification.
- vmbr0 UP, host 192.168.0.14/24, default route 192.168.0.1, resolver
  192.168.0.20, search home.arpa. No bridge/network edits.
- lab-vms: node-local LVM-thin, vg_lab_vms on nonrotational NVMe; supports images
  and rootdir, approximately 1.27 TiB free; data 29.18%, metadata 19.51% used.
  Proposed disks total 96 GiB plus cloud-init/overhead. local is a directory on
  the other local NVMe, supports import, about 16.57 GiB free. Neither is NFS.
- No candidate IP references in declared cluster VM cloud-init/CT network fields;
  no candidate AdGuard configuration references; AdGuard DHCP disabled.
  Proposed forward names and reverse IP lookups return NXDOMAIN; targeted ICMP
  probes receive no reply. None proves absence of an offline/static LAN device.
- Router 192.168.0.1 HTTP entry point reachable, but no authenticated DHCP range,
  active leases or reservations available to this environment. Operator evidence
  requested. **Authoritative IP availability remains UNVERIFIED.** Do not infer
  availability from failed ping, DNS absence or the Proxmox inventory.
- Strict host-key-verified SSH succeeds to root@192.168.0.14. Accepted controller
  public-key fingerprint matches tracked keys/doku-lab-admin.pub. No private key
  read/copied. Future guest keys cannot be verified until creation; bootstrap
  trust must be established independently before convergence.
- Host naming blocker: short pve-lab does not resolve from this controller;
  pve-lab.home.arpa also returned NXDOMAIN at AdGuard. Current start playbook
  delegates to the node name, explicitly using that as ansible_host. Before
  start, separately review use of the existing inventory's IP mapping or an
  approved SSH/DNS mapping. Do not disable host-key checks; no fix applied here.
- Existing workstation provider uses insecure=true at https://192.168.0.10:8006/;
  the private controller proposal uses that same endpoint and explicit true.
  Normal TLS verification fails there (also at pve-lab's API). Proposed Stage A
  inputs should explicitly reuse proxmox_insecure=true under that convention,
  not inherit its false default or redesign PKI in this milestone.
- Infisical CLI available; INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET absent
  in this process. No login, secret lookup or provider-auth test performed.
  Later authorized plan must use the existing authenticated operator shell and
  INFISICAL_RUN; effective API permissions for VM/image/storage remain untested.

### Image provenance

Proposed pinned source:
https://cloud.debian.org/images/cloud/trixie/20260914-2601/debian-13-generic-amd64-20260914-2601.qcow2

433651712 bytes streamed on controller only, not retained/imported. SHA512
matches Debian's SHA512SUMS fetched over verified HTTPS; no detached signature
verification claimed. Derived SHA256:
`b6e3a4dac69b38d55a763b1752e8fd7bb12e3948672a79fee4ef13fa53839d2f`.
Image bootability on these guests remains untested.

### Gate and expected changes

Expected source-level scope: one proxmox_download_file.linux["pve-lab/local"]
and three module.servers VM resources, **4 add / 0 change / 0 destroy expected**.
This is NOT a plan result. Guests remain stopped, on_boot false, with no GPU/USB/
hook and destruction protection retained. All existing roots/states stay separate.

First obtain router DHCP range/reservations/lease and independent static-address
confirmation for .33-.35 (or revise the candidate). Then request explicit approval
of the exact allocation and new-resource-only plan. Do not execute stage-a-plan
until that approval; apply/image import/start/convergence remain separate gates.
The host-name mapping issue blocks later start, not the proposed API plan.

## Approved allocation and plan handoff - 2026-09-26

Operator personally confirmed VMIDs 303-305 free cluster-wide and .33-.35 free
and outside the Fizz DHCP pool. This is authoritative operator evidence, not an
agent claim to have read router settings. No repeat audit or confirmation needed.
Previous capacity, storage, image and trust observations remain dated evidence.

| Key | Approved VMID | Approved hostname | Approved IPv4 |
| --- | --- | --- | --- |
| server-1 | 303 | k3s-server-1 | 192.168.0.33/24 |
| server-2 | 304 | k3s-server-2 | 192.168.0.34/24 |
| server-3 | 305 | k3s-server-3 | 192.168.0.35/24 |

All on pve-lab (management 192.168.0.14), 2 vCPU / 4096 MiB / 32 GiB each;
vmbr0, gateway .1, DNS .20, local image import and lab-vms local disks.
Created mode-0600 ignored terraform/stacks/pve-lab-k3s/terraform.tfvars with
those inputs, the previously verified Debian image/hash, API endpoint .10 and
explicit proxmox_insecure=true consistent with existing roots. No credentials
in inputs. No reuse of Task035's VM603/.32; no existing Terraform root changed.

Start mapping fix: Make loads the existing homelab host inventory plus generated
guest inventory. Delegation uses hostvars for pve-lab -> 192.168.0.14; removed
the task-level override that forced the unresolved short name. Missing Proxmox
host mapping fails closed, SSH host-key checking explicitly remains enabled.
Offline merged-inventory regression checks the management IP separately from
the guest IP. No SSH configuration or live DNS change; no start executed.

Both INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET are absent in the agent's
runtime. No alternate auth, secret lookup or provider plan was attempted.
Run the already-approved plan from the repository root in the authenticated operator shell:

```sh
make stage-a-plan STAGE_A_ALLOCATION_REVIEWED=yes
```

Expected scope remains one image download resource and three new VM resources,
4 add / 0 change / 0 destroy. **No actual plan result or plan hash exists yet.**
After execution, inspect the complete saved plan and its printed SHA256 before
requesting separate approval to apply that exact plan. Stop on any existing
resource change, replacement, workstation mapping or state-ownership change.
Do not run stage-a-apply/start/configure or install K3s in this milestone.

Local validation: make stage-a-check PASS (15 mocked VM cases, merged inventory
management-IP and approval guards, Ansible syntax); configuration/script parser,
Terraform fmt, documentation links and git diff --check PASS. Private input file
is ignored and mode0600. Existing state-file checksums unchanged before/after;
tracked Terraform roots, inventory and workstation host role have no diff.
These are local checks, not verification of an actual provider plan. Publication
CI for the mapping fix is reported against its exact SHA at delivery.

## Live guest qualification - 2026-09-26

This supersedes the earlier plan/authentication and independent SSH-trust gates.
Operator reports exact reviewed apply **4 added / 0 changed / 0 destroyed**,
manual startup, then identity-checked `stage-a-start` correctly skipping all
already-running VMs. No repeat startup, plan or apply was performed here.

Initial Proxmox reads confirmed running names/IDs, 2 cores, 4096 MiB, 32-GiB
local lab-vms disks, expected cloud-init IPs and no GPU/USB/hook settings.
Operator confirms workstations remain off; this work did not alter any existing
root, state, workstation configuration, disks or mappings.

Operator explicitly authorized TOFU for these disposable guests only. OpenSSH
`StrictHostKeyChecking=accept-new` enrolled three new ED25519 entries into the
normal controller known_hosts, with no conflicts. This did NOT independently
authenticate first contact. Every subsequent SSH/Ansible connection explicitly
used strict checking. Login used the existing administration identity as debian;
no private key was generated, copied or exported. `sudo -n` succeeded on all.

| Guest | Verified network / OS / disk | First baseline | Second baseline |
| --- | --- | --- | --- |
| 303 k3s-server-1 | .33/24, Debian 13.7, 32-GiB sda, ext4 root on sda1 | ok=6 changed=2 failed=0 unreachable=0 | ok=6 changed=0 failed=0 unreachable=0 |
| 304 k3s-server-2 | .34/24, Debian 13.7, 32-GiB sda, ext4 root on sda1 | ok=6 changed=2 failed=0 unreachable=0 | ok=6 changed=0 failed=0 unreachable=0 |
| 305 k3s-server-3 | .35/24, Debian 13.7, 32-GiB sda, ext4 root on sda1 | ok=6 changed=2 failed=0 unreachable=0 | ok=6 changed=0 failed=0 unreachable=0 |

All: gateway .1 reachable, resolver .20 observed through resolvectl, home.arpa
search domain, deb.debian.org resolution successful, NTP synchronized. Cloud-init
finished (`status: done`, errors empty), with `degraded done` solely from the
deprecated string `user` field (scheduled removal in cloud-init 27.2). Record as
a future image/Proxmox cloud-init compatibility follow-up, not a failed bootstrap;
no generated metadata or Proxmox configuration rewritten to suppress it.

Both runs used existing `make stage-a-configure STAGE_A_CONFIGURE_APPROVED=yes`,
with ANSIBLE_HOST_KEY_CHECKING=True and SSH StrictHostKeyChecking=yes. First run
installed qemu-guest-agent and started its service; CA/curl/Python/time packages
and hostnames were already correct. Second convergence made zero changes.
All five required packages present; qemu-guest-agent 1:10.0.13+ds-0+deb13u1 active
(unit reported static), systemd-timesyncd 257.13-1~deb13u1 active/enabled;
NTPSynchronized=yes, zero failed systemd units. Proxmox guest-agent ping succeeded
for each VM after convergence. No reboot/failure drill was performed.

`terraform/stacks/pve-lab-k3s/terraform.tfstate` is now the seventh real local
authority: one shared image and three server resources. No state was exported,
migrated or modified by this qualification. See the updated
[recovery inventory and follow-up](../docs/recovery-kit-preparation.md#stage-a-authority-update---2026-09-26)
and Task040; its six-root verifier must not be mistaken for complete current
inventory. No recovery implementation or accepted contract changed.

No baseline code fix was necessary. Local PASS: Stage A regression tests,
baseline Ansible syntax (temporary local directory after sandbox denied the
default Ansible temp path), configuration/script checks (55 YAML, 10 Python,
21 shell), 65 local Markdown links/anchors and git diff --check. Static inventory
has no k3s_lab group; its syntax-only warning is expected, while both live runs
used applied-output inventory successfully. Exact Forgejo/GitHub SHA is reported
at delivery. Task110 remains unstarted:
require separate assignment/approval, pinned K3s integrity/version, API/TLS SANs,
pod/service CIDRs, CNI/bundled-component ownership and lab-token handling decisions.

Closure: operator accepted this evidence on 2026-09-26. Documentation commit
3320af04beb909dca075a3e1488b6fed200ea1f1 passed Forgejo run31 (API142); GitHub
main matched exactly. Task110 repository-only implementation is now separately
assigned; no installation or real token generation authorized by this closure.
