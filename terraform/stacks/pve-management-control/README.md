# pve-management-control — management VM `mgmt-control-01`

OpenTofu root (ADR-003) that creates the operator workstation on the standalone `pve-management` host:
a regular **Ubuntu Desktop** installed from the official ISO by autoinstall (ADR-009). Configuration is
`ansible/playbooks/configure-mgmt-control.yml`. Plan, decisions and acceptance tests:
[INV-pve-management-bootstrap](../../../docs/investigations/pve-management-bootstrap.md).

Runs **only from the operator workstation** (ADR-008). CT301 never receives these credentials.

## Prerequisites (operator)

1. OpenTofu 1.13.9 (`brew install opentofu`), Python controller environment (`make setup-controller`).
2. TLS trust for the `pve-management` certificate: add the host's `pve-root-ca.pem` to the workstation
   trust store (macOS Keychain, "Always Trust" for SSL), after checking its fingerprint on the host console.
   `PVE_CA_FILE` is honoured by `mgmt-discover` only; OpenTofu uses the system store.
3. A dedicated API identity and token (exact privileges in the investigation document), stored in
   Infisical under `/pve-management` as `PROXMOX_VE_API_TOKEN`, or exported for `MGMT_INPUT_SOURCE=env`.
4. The SSH host key of `pve-management` verified on the console; stale `pve-infra` entries for
   192.168.0.10 removed from `known_hosts` by the operator.

## Workflow

| Step | Command | Effect |
|------|---------|--------|
| Offline check | `make mgmt-check` | fmt, validate, mocked `tofu test`, Ansible syntax, guard tests |
| Discovery | `make mgmt-discover MGMT_INPUT_SOURCE=infisical MGMT_DISCOVER_ARGS="--image-datastore … --disk-datastore … --bridge …"` | Read-only GETs: version, standalone status, storages, bridges, used VMIDs, token privileges |
| Profile | copy `terraform.tfvars.example` to `terraform.tfvars` | Replace every PROPOSED value with discovered/confirmed values |
| Plan | `make mgmt-plan MGMT_ALLOCATION_REVIEWED=yes MGMT_INPUT_SOURCE=infisical` | Saved plan `mgmt.tfplan` + SHA256; first install: 1 ISO download, 1 VM, nothing else |
| Passwords | write `.local/mgmt-control/ubuntu-password` and `.local/mgmt-control/rdp-password` (one line each, mode 0600, git-ignored) | Linux account (console, GDM, RDP stage 2, sudo) and RDP stage 1 |
| Seed | `make mgmt-autoinstall-serve MGMT_SEED_BIND=<this host's LAN IP>` (keep running during the install; it must match `autoinstall_seed_url`) | Serves the autoinstall rendered from the same variables, with the sha512-crypt hash of the account password; stop it after the install |
| Apply | `make mgmt-apply MGMT_APPLY_APPROVED=yes MGMT_PLAN_SHA256=<sha> MGMT_INPUT_SOURCE=infisical` | **Mutates pve-management.** Applies exactly the reviewed plan |
| Install | Proxmox console of VM 100: confirm the automated installation once | Ubuntu Desktop installs and reboots into the GDM login screen (~15 min) |
| Backup | `make mgmt-state-backup MGMT_BACKUP_DIR=<off-machine dir> AGE_RECIPIENTS_FILE=<recipients>` | age-encrypted, dated copy of the state |
| Configure | `make mgmt-configure MGMT_CONFIGURE_APPROVED=yes MGMT_SOURCE_COMMIT=<full sha on the GitHub mirror>` | Ansible baseline, toolchain and admin workstation (reads both password files on the controller, sets each once, never logs them) |
| Remote access | Thincast → RDP `192.168.0.39:3389` | GNOME Remote Login, two stages (below) |
| Idempotency | `make mgmt-plan …` again | Must report no changes |

## Reinstalling VM 100

`prevent_destroy` protects the VM, so a reinstall keeps the VM and its state and wipes the disk in place:

1. Write the password files; plan/apply if the template or `autoinstall_seed_url` changed (the seed is
   read from the `autoinstall_user_data` output, which only an apply refreshes).
2. `make mgmt-autoinstall-serve MGMT_SEED_BIND=<LAN IP> MGMT_SEED_SHUTDOWN=poweroff`.
3. With the token (`VM.Config.Options`, `VM.PowerMgmt`): set `boot=order=ide2;scsi0`, stop and start
   VM 100 (a cold start applies the boot order); confirm the installation on the console. The autoinstall
   erases the disk.
4. When the VM has powered off: set `boot=order=scsi0;ide2`, start it, check SSH, stop the seed server.
5. `make mgmt-plan` must report no changes; then `mgmt-configure`.

The SSH key and the keys-only sshd drop-in are written by late-commands: cloud-init is disabled on the
installed system and never applies the installer's SSH settings.

## Remote login (GNOME Remote Login, ADR-009)

1. **RDP stage**: Thincast connects to `192.168.0.39:3389` with user `ubuntu` and the *RDP password*.
   Compare the certificate fingerprint with the one `mgmt-configure` prints, then accept it.
2. **Linux stage**: the GDM login screen appears; log in as `ubuntu` with the *desktop password*. The
   client is redirected to the new headless GNOME session (it may reconnect once).

Only `admin_workstation_rdp_allowed_networks` reach 3389/tcp. SSH (key-only) and the Proxmox console stay
available when RDP fails. Post-deployment checks: both stages; disconnect and reconnect to the session;
a connection from outside the allowed networks is refused; a second `mgmt-configure` reports no changes
and both passwords still work; SSH and the console still log in.

## State

Local backend: `terraform.tfstate` beside this file on the operator workstation (git-ignored), one
operator at a time (OpenTofu's local lock file guards concurrent runs on that machine). After every
apply, run `mgmt-state-backup` to an off-machine location. Restore = decrypt the latest `.tfstate.age`
into this directory and confirm `make mgmt-plan` reports no changes. A shared remote backend with
locking is required before any second executor (runner) may apply (TASK-010).
