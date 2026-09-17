# Forgejo Runner Container

This root is the Terraform representation of the existing `forgejo-runner`
container on `pve-compute`. It is intentionally parameterized because the
authoritative VMID, storage, network, operating system template, and resource
allocations must be collected from Proxmox before adoption.

## Adoption procedure

1. Record the existing container configuration without changing it. Collect
   the VMID, rootfs datastore and size, operating system template file ID, CPU,
   memory, swap, feature flags, bridge, MAC address, firewall, IP, gateway,
   DNS, tags, and boot settings.
2. Create a private `terraform.tfvars` with those values and the Proxmox API
   endpoint. Do not commit that file.
3. Initialize and validate this root, then import the existing container:

   ```text
   terraform -chdir=terraform/stacks/pve-compute-forgejo-runner import \
     proxmox_virtual_environment_container.forgejo_runner pve-compute/<VMID>
   ```

4. Run a normal plan and reconcile only intentional drift. Do not apply until
   the plan is reviewed and the imported state matches the live container.

The import command is documentation only; this repository does not run it
automatically and does not contain live VMID or credential values.
