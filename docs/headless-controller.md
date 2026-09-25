# Headless recovery-controller capability

Task035: repository implementation only, no VM allocation/deployment or guest
convergence. A green mocked test is not a live no-op or a working cloud image.

## Ownership and capabilities

Existing workstation addresses and ordinary configuration stay in place. Only
PCI/USB blocks become conditional on hardware_profiles; omitted entries retain
the current GPU and four USB devices in their original order. Do not apply an
override to an existing workstation without its own reviewed plan. This does
not remove its existing hook/tags or turn an adopted workstation into a new VM.

The small pve-lab-controller root provisions a checksummed Linux cloud disk and
one VM with local state. It is reusable through a required profile, not a copy
of the Windows/EFI/TPM/workstation stack or a migration into a new module. No
passthrough, workstation tag, gaming roles or arbitration hook is requested.
It can coexist with the gaming workstation subject to capacity checks. Guest
software is owned by configure-recovery-controller.yml, not cloud-init scripts.

## Review before deployment

1. Select a versioned Debian13 AMD64 cloud qcow2 URL and independently verify its
   SHA256. Existing Ubuntu8101 is flagged a template; Fedora8200 is not. Neither
   was qualified for this controller. No unsafe clone fallback is provided.
2. Propose VMID/IP/CIDR/gateway/DNS, bridge and image/disk datastores on pve-lab;
   verify cluster-wide ID absence, IP allocation and storage/image support/live
   capacity read-only. An empty value must fail, not choose an allocation.
3. Populate ignored terraform/stacks/pve-lab-controller/terraform.tfvars with
   proxmox_endpoint, deliberate proxmox_insecure choice and profile fields from
   variables.tf. Synthetic test values are NOT available LAN allocations.
   Root uses the tracked admin public key; private-key availability/trust must
   be confirmed without copying it to CI or the guest.
4. After allocation review, run `make controller-plan CONTROLLER_ALLOCATION_REVIEWED=yes`
   in the existing authenticated operator environment. Expect only one image
   download and one new VM. Inspect all planned fields, including no hostpci,
   USB or hook; no other roots/states participate. Ask for explicit apply
   approval against the saved controller.tfplan before
   `make controller-apply CONTROLLER_APPLY_APPROVED=yes`.
5. VM remains stopped; starting it and guest convergence need separate approval.
   Provide a private inventory with group recovery_controller, reviewed IP,
   ansible_user=debian and independently verified SSH trust. Run the playbook
   with recovery_source_commit set to a full approved Git SHA only after approval.
   It installs Debian13 Python/venv, Git/Make and checksummed Terraform1.16.1,
   clones that exact public GitHub revision and runs existing setup-controller.
   Direct Python/collection versions come from existing dependency files;
   OS and transitive packages still depend on repositories, not a hermetic lock.
6. The test VM must retrieve ciphertext independently and decrypt into private
   storage only after a separate drill approval. Block internal-service access
   during static bootstrap; external package/GitHub access remains required.
   Public DNS or reviewed static access must not depend solely on AdGuard.
   pve-lab hosting proves controller replacement, NOT recovery from loss of pve-lab.

Normal controller-plan/apply reuse Universal Auth. They are not the future
control-plane-independent interface from Task050. No production kit goes into
this guest merely because it was provisioned. Cleanup requires a reviewed
destroy operation; prevent_destroy must not be disabled automatically.

## Validation and limits

`make controller-check` runs copied code-only mocked Terraform plans and Ansible
syntax. Five Terraform cases cover existing profiles, optional hardware, invalid
mapping, headless configuration and invalid allocation. Snapshot guards retain
all original ordinary VM fields and locals (IDs/disks/MAC/SMBIOS/lifecycle).
No real state, private tfvars, personal SSH files or API credentials enter tests.
Eight roots are covered by readonly/backend-disabled CI validation.
Cloud-init connectivity, actual disk import, capacity, no-op live workstation
plan and guest convergence remain NOT TESTED. No state move/import is needed.
