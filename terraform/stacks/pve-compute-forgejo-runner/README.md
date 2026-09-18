# Forgejo Runner Container

This root is the Terraform representation of the existing `forgejo-runner`
container on `pve-compute`. `terraform.tfvars.example` records the observed
CT values and uses the available Debian 13 template as the canonical
reconstruction template. It is not evidence that this was the template used
to create CT 300.

## Adoption procedure

1. Record the existing container configuration without changing it. Confirm
   the observed values in `terraform.tfvars.example` and any provider fields
   not represented by `pct config`.
2. Create a private `terraform.tfvars` with those values and the Proxmox API
   endpoint. Do not commit that file.
3. Initialize and validate this root, then import the existing container:

   ```text
   terraform -chdir=terraform/stacks/pve-compute-forgejo-runner import \
     proxmox_virtual_environment_container.forgejo_runner pve-compute/<VMID>
   ```

4. Run a normal plan and reconcile only intentional drift. Do not apply until
   the plan is reviewed and the imported state matches the live container.

The repository Makefile provides the explicit adoption commands:

    make runner-import
    make runner-live-plan

Both commands require the ignored private terraform.tfvars and use the
existing INFISICAL_RUN Universal Auth workflow for runtime Proxmox provider
credentials. They do not use a human Infisical session or persist credentials
in the repository. runner-live-plan is the first post-import plan command; do
not run an apply from this root until its output is reviewed.

The import command is documentation only; this repository does not run it
automatically. The private `terraform.tfvars` and local state remain ignored.

The provider does not recover the historical OS template provenance from the
existing CT configuration. The resource therefore keeps the canonical Debian
13 template for future reconstruction but ignores only that imported
template-provenance field after adoption. The observed operating-system type
(`debian`) and IPv6 DHCP configuration remain explicitly modeled.

The runner CT does not have a per-container DNS setting in Proxmox. Its
`/etc/resolv.conf` is generated from the `pve-compute` node DNS configuration,
so DNS is inherited runtime behavior rather than Terraform-owned CT
initialization. It is intentionally omitted from this Terraform root to avoid
creating a second owner.
