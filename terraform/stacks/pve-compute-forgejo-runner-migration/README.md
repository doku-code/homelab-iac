# Forgejo Runner Migration Container

This Terraform root creates a fresh Forgejo Runner LXC on `pve-compute`.
It is intentionally separate from the imported CT 300 adoption root and has
no import-specific lifecycle normalization.

The target is VMID 301 at `192.168.0.31/24`, using the Debian 13 standard
template, 4 cores, 6144 MiB RAM, 512 MiB swap, a 38 GiB `local-lvm` disk,
nesting, and deterministic DNS `192.168.0.20`.

Create a private `terraform.tfvars` from the example, then run through the
repository Make targets:

```text
make runner-migration-plan
make runner-migration-apply
```

The apply target is intentionally separate from the existing CT 300 targets.
Review the plan and confirm that it creates only VMID 301 before applying.
