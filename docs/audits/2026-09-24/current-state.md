# Current state

Audit: 2026-09-24. Source baseline: `fd4435e`, branch `main`.
This assessment is not authorization to execute the roadmap.

## Evidence labels

- **VERIFIED IN SOURCE CODE**: inspected implementation at this baseline.
- **VERIFIED ON LIVE INFRASTRUCTURE**: fresh read-only observation this audit;
  a running process or HTTP response is not a recovery or functional test.
- **REPORTED BY PREVIOUS QUALIFICATION**: dated repository evidence, not rerun.
- **DOCUMENTED BUT NOT VERIFIED**: assertion/runbook without current proof.
- **PROPOSED ONLY**: future design, not implemented.
- **MISSING**: no corresponding implementation/evidence found here.
- **UNKNOWN / ACCESS BLOCKED**: insufficient authorized access or evidence.

## Git and scope

**VERIFIED IN SOURCE CODE:** initial status `main...origin/main [ahead 2]`,
with only local `AGENTS.md` untracked. Only remote: Forgejo origin at
`https://git.doku-lab.net/Homelab/homelab-iac.git`. Read-only `ls-remote`
confirmed live main at `0d3c4d0a69add4b1cb20a45973f23c069a6322d1`.
Unpublished to that remote:

- `1abda76 feat(terraform): schedule and qualify PostgreSQL logical backups`
- `fd4435e docs(terraform): record DNS and scheduled backup qualification`

**DOCUMENTED BUT NOT VERIFIED:** operator reports a GitHub recovery copy.
No GitHub remote is configured; freshness and these commits' publication there
were not established. `homelab-iac-plan-directeur.md` was not found in this
repository, and no authorized external path was supplied.

Inspected README, Makefile, dependencies, Ansible configuration/inventories,
roles/playbooks/templates, Terraform roots/provider locks, both workflows,
monitoring composition/provisioning, CI image source, tests, qualification script,
runner/backend documentation, ignore rules and structural state metadata.
No sibling repository inspected; no private state attributes or secret values
printed. Only audit documents added; no commits or live configuration changes.

## Code inventory

**VERIFIED IN SOURCE CODE:**

| Category | Count and implementation |
| --- | --- |
| Terraform roots | 7: six stacks and one cloud-image VM example |
| Terraform child modules | 0; resources directly in roots |
| Ansible roles | 9: dev, forgejo_runner, gaming, garage, guest_base, node_exporter, pve_workstation_host, tfstate, workstation |
| Playbooks | 13 |
| Inventory entry files | 7, plus three group_vars and one hardware host_vars file |
| Forgejo workflows | 2: validation and manual ci-base publication |
| Service composition | One monitoring Compose stack, six services |
| CI image | services/ci-images/base/Dockerfile |
| Test programs | Three in tests; separate PostgreSQL qualification script |

Provider bpg/proxmox 0.112.0 pinned. Python requirements pin Ansible 14.4.0,
infisicalsdk 1.0.16 and Paramiko 4.0.0; six direct collections pinned.
`make setup-controller` rebuilds `.venv` but defaults to local `python3`;
CI explicitly installs checksummed CPython 3.14.0. Transitive Python dependencies
are not a hashed lock; Galaxy has no explicit repository-isolated collection
path. Useful repeatability, not a hermetic/offline controller.

## Live and source ownership

**VERIFIED ON LIVE INFRASTRUCTURE:** four nodes online; 25 guests including
five flagged templates; 14 guests running. Running is not application health.

| Component | Hosting and fresh evidence | Source ownership / limitation |
| --- | --- | --- |
| pve-core | Online; monitoring, Infisical, Garage, tfstate and others | Proxmox installation/network/storage not provisioned here |
| pve-compute | Online; CT301 and VM401 running | Host foundation manual; runner CT modeled |
| pve-lab | Online; VM502 running, other managed workstations stopped | Five adopted VMs; workstation host role manages passthrough/affinity/hooks |
| pve-infra | Online; CT200-204 running | Service CTs and host foundation not Terraform-managed here |
| TrueNAS | Proxmox NFS and Caddy Forgejo upstream point to its endpoint | Direct datasets/apps/ACLs/encryption/storage topology UNKNOWN / ACCESS BLOCKED |
| PBS | Backup storage reachable; seven CT300 snapshots listed | No PBS root/role; independent physical failure domain and full restore unverified |
| PostgreSQL CT300 | pve-core; PostgreSQL 17.11 active | pve-core-tfstate + tfstate role; loopback qualification service, not production backend |
| Runner CT301 | pve-compute; forgejo-runner active, Podman 5.4.2 | pve-compute-forgejo-runner-migration + forgejo_runner; identity/registry auth from Infisical |
| Garage CT209 | pve-core; garage active | pve-core-garage + garage role; source pins 2.4.1; historical locking rejection remains |
| Infisical VM207 | pve-core running; HTTPS endpoint 200 | No server provisioning/recovery code; Caddy upstream .27:80 |
| Forgejo and registry | HTTPS version endpoint 200; Caddy upstream on TrueNAS | No server IaC; authenticated registry operations not retested |
| AdGuard CT200 | pve-infra; AdGuardHome.service running; service DNS resolves | Rewrites/users/settings manually managed |
| Caddy CT204 | pve-infra; caddy/cloudflared running | Local Caddyfile and Cloudflare credential-file presence verified; no role/root |
| Monitoring VM208 | pve-core running; Prometheus readiness/Grafana health HTTP 200 | deb13-monitoring + bootstrap/deploy playbooks + Compose; SSH blocked by changed host key |
| Workstations 501/502/503/601/602 | pve-lab; only 502 running | Hardware adoption and guest capability roles, not demonstrated OS reconstruction |
| Other services | homepage201, wiki-js202, print-server203, vaultwarden206, Windows400/401 running | No complete IaC ownership found; technical state recovery inventory needed |
| Extra guests/templates | 8100/8200 stopped, not flagged templates; 8101/9001/9101/9102/9103 flagged templates | Manually maintained; template-like names do not prove template status |

Storage: local directory, local-lvm LVM-thin, lab-vms LVM-thin restricted to
pve-lab, pve_library NFS on TrueNAS, and pbs backup-store. Redundancy, encryption,
capacity and failure-domain independence unverified. Local CT disks do not
automatically depend on TrueNAS.

Runner source maps labels homelab-iac and forgejo-theme to
`git.doku-lab.net/doku-code/ci-base:1.0.0`, and cem to
`git.doku-lab.net/cem/cem-ci:1.0.3`. Fresh allowlisted inspection confirmed three
instance-root connection URLs and docker_host="-"; local image inventory contains
the current images and historical caches including localhost/cem-ci:latest.
Cached legacy images are not proof of active workflow use and were left alone.

## Mutable technical application state

**MISSING:** complete recoverable inventory beyond Git. This concerns technical
service configuration/identity, not a general user-data backup project.

| Service | Recovery material beyond declarative configuration |
| --- | --- |
| Infisical | Database, application encryption keys, identities, policies, projects and secret versions; database alone may be insufficient |
| Forgejo | Database, app keys/settings, permissions, Actions secrets, registrations, repositories, package blobs and matching metadata |
| AdGuard/Caddy | Rewrites/upstreams/admin settings, tunnel identity if needed, ACME account or tested reissuance path |
| TrueNAS/PBS | System configuration, datasets/ACLs, encryption recovery keys where applicable, datastore access/trust |
| Runner | Matching UUID/token registrations and registry access; caches disposable; deliberate re-registration is an alternative, not automatic reconstruction |
| PostgreSQL | Database states, roles/ownership, settings, future TLS/trust; same-cluster logical restore is not bare-cluster recovery |
| Garage | /var/lib/garage/meta, /var/lib/garage/data, layout and RPC identity together |
| Monitoring | Git-provisioned dashboards/rules plus UI-created settings/users/dashboards and alert silences in volumes |
| Workstations | Installed OS/template and technical software configuration; disk geometry is insufficient |

## Concrete findings

1. **VERIFIED IN SOURCE CODE:** workstation `locals.tf` lines 37/67/97/127/157
   use template=null. Hardware adoption does not reproduce bootable OS disks.
   PCI/USB mappings are created if missing, not fully reconciled if changed.
2. **VERIFIED IN SOURCE CODE:** `ansible/roles/node_exporter/tasks/main.yml:20`
   deploys monitoring Compose with monitoring-only secret variables, an unrelated
   responsibility and potential failure on exporter-only hosts.
3. **VERIFIED IN SOURCE CODE:** monitoring `vm.tf:83` uses the DNS resolver
   as gateway, unlike new CTs. Live routing UNKNOWN because SSH trust failed.
   Service reachability does not prove that configured default route is correct.
4. **VERIFIED IN SOURCE CODE:** old runner state/inventories/Make commands
   remain. Historical root `variables.tf:17` rejects VMID300, now PostgreSQL.
   Retire ambiguity separately; never reuse old runner state for the new host.
5. **VERIFIED IN SOURCE CODE:** Make semantics differ: reviewed saved plans for
   PG/Garage versus auto-approved re-plan/apply for runner; workstation plan
   formats source and uses a shared temporary pathname. CT301 bootstrap
   deliberately stops the daemon; it is not reconcile.
6. **VERIFIED IN SOURCE CODE:** monitoring uses alternate Universal Auth names
   and interactive setup; login/read lack runner-style check-mode overrides.
7. **VERIFIED IN SOURCE CODE:** CI validates three roots only and runs runner
   tests, not PG backup tests. No second-profile or complete recovery gate.
8. **DOCUMENTED BUT NOT VERIFIED:** older docs contain superseded CT300/S3
   recommendations. This audit preserves the requested self-hosted backend
   direction; PostgreSQL versus future Consul remains undecided.

## Validation this audit

| Check | Result / limit |
| --- | --- |
| Terraform fmt -check -recursive terraform | PASS; no formatting changes |
| Terraform validate | Six stacks PASS; provider schema startup needed approved execution outside sandbox |
| Example validate | BLOCKED: provider not cached; no init/download performed |
| Ansible syntax | 13 playbooks PASS with static homelab inventory; not proof of live inventory suitability |
| YAML parsing | 51 tracked YAML files PASS |
| Runner regression/template tests | 20 synthetic localhost cases PASS, including three instance-root URLs/current images |
| Backup tests | Two offline mocked tests PASS; no live DB/service calls |
| Artifact hygiene | No tracked state/plan/private tfvars or private-key markers found; ignore paths checked; not a full historical secret scan |
| Gitleaks | Not installed locally; present in image but not invoked by validation workflow |
| Compose/promtool/live idempotence | Source coverage inspected; not rerun in this audit |
| Audit documentation | Six files checked for relative links, balanced code fences and whitespace; tracked diff unchanged |

Garage and PG qualification programs perform live mutations and were not run.
No existing Terraform state was migrated.
