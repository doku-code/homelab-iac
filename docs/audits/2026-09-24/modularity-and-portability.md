# Modularity and portability

Evidence labels: [current-state](current-state.md). No refactoring performed.

## Layers that actually exist

**VERIFIED IN SOURCE CODE:** environment-specific Terraform roots, Ansible roles,
static/dynamic inventories, one monitoring Compose composition, Make workflows
and two CI workflows. Generic child modules and a service-blueprint layer are
MISSING. Existing roles vary from capability-oriented to host-specific; a role
directory does not itself make its contents reusable.

Terraform owns guest resources; Ansible owns guest OS/services and workstation
host hardware policy; Compose owns monitoring processes; Infisical delivers
secrets; Make coordinates operator commands. Preserve these divisions.
CPU affinity and hook ownership is intentionally excluded from workstation
Terraform reconciliation and handled by Ansible. Do not remove lifecycle
exclusions without checking that ownership. Separate incidental duplication
from necessary separation between infrastructure and guest configuration.

## Environment coupling

| Concern | Actual coupling | Small future interface |
| --- | --- | --- |
| Placement | Literal Proxmox node names across roots | Environment selects node, no automatic scheduler |
| Compute | Fixed CPU/RAM/swap/disk; workstation host CPU/affinity | Service minimums plus reviewed environment overrides |
| Storage | local-lvm/lab-vms/local IDs and NFS library | Explicit disk/template/snippet datastore IDs and required content capabilities |
| Templates | Named Debian13 CT template; monitoring latest cloud image; workstation null clone sources | Verified artifact/template reference and checksum/provenance where available; separate template creation policy |
| Network | vmbr0, fixed IP/gateway/resolver/domain | Environment allocation object; optional VLAN only when supported/tested, not an invented current VLAN design |
| Inventory | Repeated IP/host identity in Terraform and Ansible | One reviewed non-secret allocation source or explicit outputs-to-inventory contract |
| Public endpoints | doku-lab.net/Infisical paths/project metadata | Explicit service endpoint and secret-reference inputs, never secret values in profiles |
| Hardware | GPU PCI IDs, USB mappings, IOMMU, CPU sets, pve-lab assertion | Keep physical host profiles specific; validate capabilities before applying |
| Controller | Home-directory SSH key defaults, global Galaxy path, local Python | Explicit controller/toolchain/trust inputs; platform checks |
| Workstations | Windows OpenSSH/PowerShell/winget and Linux guest-agent assumptions | Document OS prerequisites and qualify actual images before reuse |

**VERIFIED IN SOURCE CODE:** `terraform/stacks/pve-lab-workstations/{locals,vms,hardware}.tf`
and `ansible/inventories/host_vars/pve-lab.yml` are intentionally hardware-bound.
Different hardware may require real compatibility work; variables cannot make
GPU/USB passthrough portable by themselves. No second-environment test exists.

## Reuse candidates

All interfaces below are **PROPOSED ONLY**, not implemented modules.

| Candidate | Interface and outputs | Prerequisites / hidden coupling | Evidence needed before extraction |
| --- | --- | --- | --- |
| Basic Debian CT | node, ID, template, datastore, sizing, bridge/address/DNS, public management key; output ID/address | Compatible Proxmox/template, existing storage/bridge; safety policy not hidden in universal defaults | Two isolated deployments on different profiles, no-diff reconcile, allocation failure checks, documented state-address-preserving extraction |
| Forgejo runner role | pinned binary/checksum, instance endpoint/connections, labels, runtime settings, registry references; service state | Debian/rootful Podman, privileged socket trust, Infisical integration currently in caller, site-specific defaults | Synthetic rendering already useful; add fresh-host/idempotence/recovery tests before making generic |
| PostgreSQL host/backup role | major version, listen/auth policy, backup path/schedule; readiness/recovery evidence | Current role hard-asserts .30/tfstate/Debian13, fixed cluster paths; production TLS/identity policy unfinished | Finish candidate gates and isolated restore first; preserve security policy explicitly |
| Monitoring composition | image versions, target inventory, endpoints, secret references; health checks | Literal hosts/ports, mutable Grafana settings, exporter task duplication | Static config, secret-safe render, disposable deployment/restore; no need for a framework |
| Guest capabilities | OS support/packages/user assumptions | Windows winget and preinstalled transport; distro-dependent packages | OS matrix and idempotence; retain simple roles rather than deep composition hierarchy |
| Garage role | binary/checksum, bind/path/layout inputs | Fixed single-node local paths and .29 default; failed Terraform locking | Keep internal object-storage scope; no backend reuse claim or extraction priority |

Keep workstation hardware mappings, exact allocations, site monitoring rules,
identity policies and recovery authority environment-specific. Do not genericize
every resource. Module extraction changes resource addresses unless carefully
mapped; it must be separate from backend migration, allocation or service changes.

## Options

| Criterion | A: environment-specific roots | B: incremental monorepo modules | C: split repositories now |
| --- | --- | --- | --- |
| Maintainability | Lowest short-term disruption; repeated fixes persist | Better interfaces after real reuse; one review context | Version/release coordination added before interfaces mature |
| Complexity | Small today; coupling grows | Moderate, bounded one component at a time | Highest multi-repo dependency/tooling burden |
| Reproducibility | Can improve recovery without modules | Strong with explicit inputs plus recovery tests | Separation alone does not solve recovery |
| Proxmox portability | Manual root edits | Environment profiles + tested small modules | Potential later, currently speculative |
| Sharing | Copy/adapt code | Documented reusable subset | Convenient distribution after stable releases only |
| State risk | Minimal structural risk | Address-preserving extraction needs review | State/address/path confusion plus release coordination |
| CI/CD | Current local validation stays simple | Same-repo test matrix and caller changes | Cross-repo release/trust/pinning complexity |
| Bootstrap/recovery | Current gaps remain | Can improve independently before extraction | Additional source availability/version dependencies |
| Effort / premature abstraction | Low effort, limited reuse | Measured effort justified by two real uses | High effort; interfaces currently unproven |

Recommend **B**, retaining A's working roots while improving recovery first.
No component currently demonstrates enough cross-environment recovery/testing
to justify C immediately. Public monorepo code can already be shared without
creating release infrastructure across repositories.

## Orchestration and testing

**PROPOSED ONLY:** keep Make as a small operator interface. Read-only doctor
checks should report tool versions, trust, state presence and dependencies without
printing secrets. Bootstrap, reconcile and recover should select the same code
with distinct preconditions, writer-freeze and approval boundaries. Never
automatically adopt/import/delete resources merely because discovery found them.

Testing pyramid:

1. Offline: format, all-root provider validation, all-playbook syntax, YAML,
   shell checks, synthetic secret/render tests, backup unit tests, secret scanning.
2. Disposable guest: clean install, second convergence, declared minimum resources,
   template/image availability, application readiness and narrow negative cases.
3. Backend qualification: actual two-client operations, session failure, isolation,
   least privilege, verified final TLS, logical and full isolated restore.
4. Explicitly approved drills: new controller, no control plane, replacement node,
   recovery timing and hand-back. Never make these automatic on ordinary PRs.

**REPORTED BY PREVIOUS QUALIFICATION:** narrow runner deployment and backend
tests exist. **MISSING:** complete fresh-controller recovery, second profile,
hardware replacement, complete PBS restore and final-endpoint PG qualification.
Live Ansible check mode is not proof of idempotence; syntax is not execution.
