# deploy-runner — bootstrap Forgejo deployment runner (M003, ADR-014)

`deploy-runner-01`, VMID 302, `192.168.0.32/24`, on `pve-core` (the bootstrap runner; `pve-management` was too
small, operator decision 2026-11-17). Debian 13 cloud image, 6 vCPU, 8 GiB, 24 GiB thin disk.
This root is applied **only from the operator workstation** with `tofu@pve!mgmt` (ADR-008); the runner never
applies its own VM. Local state beside the code (git-ignored), like `pve-management-control`.

## Trust model

| Piece | Holds | Can do |
|-------|-------|--------|
| CT301 (`homelab-iac` label) | nothing | validation only; never sees `homelab-deploy` or Proxmox credentials (`tests/deploy-runner.py`) |
| Job user `runner` on the VM | runner registration (`/etc/forgejo-runner/config.yml`, 0640 root:runner) | run job steps; `sudo -u deploy /usr/local/sbin/homelab-deploy` and nothing else |
| `homelab-deploy` as `deploy` | `deploy-runner@pve!ci` token (`/etc/homelab-deploy/proxmox.env`, 0640 root:deploy), state in `/var/lib/homelab-deploy/state` | fresh clone of Forgejo `main` per run (Git config/hooks off, empty HOME, root-owned tofu CLI config); plan only the current `main` tip of an allowlisted root; apply only an unexpired (24 h) saved plan that the operator approved |
| Operator over SSH (`debian` + sudo) | — | `make deploy-runner-review` (`tofu show` on the runner) and `make deploy-runner-approve`, which writes the root-owned `/etc/homelab-deploy/approvals/<root>.sha256` |
| `deploy-runner@pve!ci` | — | create/manage guests **inside pool `ci-disposable`** only |

Gate honesty: Forgejo has no environment protection rules, and any branch can carry a workflow that targets
the `homelab-deploy` label, so `deploy.yml`'s `if:` is an activation gate, not the boundary. Such a job runs as
`runner` without credentials; through the wrapper it can at most plan the current `main` tip or trigger an
apply that the operator already approved. **Approval never comes from a job**: it is the root-owned file
written over SSH after reviewing the plan on the runner (job logs are public and a stolen registration
token could forge them). Whoever can push to `main` controls the code that runs with the token: protect
`main` in Forgejo and keep fork-PR workflows behind approval. A runner restart is refused while a
deployment holds the lock.

## Operator steps (each needs explicit approval)

1. **Allocation** (done 2026-11-17, read-only): .32 no ping/ARP reply, VMID 302 free; `pve-core` has 16 CPUs,
   ~29.6 GiB RAM available, `local` (import, 30 GiB free), `local-lvm` (848 GiB free) and vmbr0. The operator confirmed .32 is outside the pfSense DHCP pool (.100–.200). Copy `terraform.tfvars.example` to
   `terraform.tfvars`.
2. **Plan** (no change on the cluster):
   `scripts/secrets.py run /pve-management -- make deploy-runner-plan MGMT_INPUT_SOURCE=env DEPLOY_RUNNER_ALLOCATION_REVIEWED=yes DEPLOY_RUNNER_NEW_STATE=yes`
   (`DEPLOY_RUNNER_NEW_STATE=yes` only for this first creation). `tofu@pve!mgmt` holds `IaCManagementVM` on
   `/vms`, `/storage/local`, `/storage/local-lvm`, `/sdn/zones/localnetwork/vmbr0` and `/nodes/pve-management`;
   placing the VM on `pve-core` needs one more ACL (privilege change, approve it):
   `pveum acl modify /nodes/pve-core --roles IaCManagementVM --users tofu@pve --tokens 'tofu@pve!mgmt'`.
3. **Apply** the reviewed plan: `… make deploy-runner-apply MGMT_INPUT_SOURCE=env DEPLOY_RUNNER_APPLY_APPROVED=yes DEPLOY_RUNNER_PLAN_SHA256=<sha>`.
   Then verify the SSH host key on first contact (`ssh debian@192.168.0.32`, compare with the Proxmox console).
4. **Credentials** (credential creation, approve each):
   - Proxmox, on any node as root:
     ```
     pveum pool add ci-disposable --comment "Disposable CI guests (deployment runner)"
     pveum role add IaCDisposable -privs "VM.Allocate VM.Audit VM.Config.CDROM VM.Config.CPU VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit Sys.Audit"
     pveum user add deploy-runner@pve --comment "Forgejo deployment runner (ci-disposable only)"
     pveum user token add deploy-runner@pve ci --privsep 1
     for p in /pool/ci-disposable /storage/local-lvm /nodes/pve-core; do
       pveum acl modify "$p" --roles IaCDisposable --users deploy-runner@pve --tokens 'deploy-runner@pve!ci'; done
     ```
     `VM.Allocate` on the pool lets the token create guests only when they are placed in `ci-disposable`;
     storage IDs are cluster-wide (`local-lvm` on every node). No `/vms`, no `/`, no SDN (the probe has no NIC).
   - Forgejo: `Homelab/homelab-iac` → Settings → Actions → Runners → Create new runner (`deploy-runner-01`);
     note the UUID and token. Set the repository variable `DEPLOY_RUNNER_APPROVED=true` only when ready.
   - Infisical, project Homelab-IaC, env `dev`, path `/deploy-runner`: `FORGEJO_RUNNER_UUID`,
     `FORGEJO_RUNNER_TOKEN`, `DEPLOY_PROXMOX_VE_API_TOKEN` (`deploy-runner@pve!ci=<secret>`).
5. **Configure**: `scripts/secrets.py run /deploy-runner -- make deploy-runner-configure DEPLOY_RUNNER_CONFIGURE_APPROVED=yes`; a second run reports changed=0.
6. **Proof** (M003 acceptance): Forgejo → Actions → Deploy → Run workflow on `main`: `ci-disposable` / `plan`.
   Review on the runner: `make deploy-runner-review DEPLOY_ROOT=ci-disposable`; approve:
   `make deploy-runner-approve DEPLOY_RUNNER_APPROVE=yes DEPLOY_ROOT=ci-disposable DEPLOY_PLAN_SHA256=<sha>`;
   then dispatch `apply` with that SHA256. Clean up the same way with `plan-destroy`.

## Reinstall or move

`prevent_destroy` guards the VM. To move it to another node, change `profile.node` (and the endpoint if
desired) in a reviewed plan; the runner keeps no state that is not reproducible except
`/var/lib/homelab-deploy/state` (disposable roots only).
