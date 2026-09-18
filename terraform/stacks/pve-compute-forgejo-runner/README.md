# Forgejo Runner Container

This root is the Terraform representation of the existing `forgejo-runner`
container on `pve-compute`. `terraform.tfvars.example` records the observed
CT values and uses the available Debian 13 template as the canonical
reconstruction template. It is not evidence that this was the template used
to create CT 300.

## Adoption procedure

1. Record the existing container configuration without changing it. Confirm
   the observed values in `terraform.tfvars.example`, especially DNS and any
   provider fields not represented by `pct config`.
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
automatically. The private `terraform.tfvars` and local state remain ignored.

The provider does not recover the historical OS template provenance from the
existing CT configuration. Keep the canonical template for future
reconstruction separate from any import-time provider normalization, and do
not hide an unresolved replacement behind `ignore_changes`.
