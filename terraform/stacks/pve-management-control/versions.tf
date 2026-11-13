# OpenTofu root (ADR-003): run it with `tofu`, through the mgmt-* Make targets.
# Local state on the operator workstation only; see README.md for backup and locking.
terraform {
  required_version = ">= 1.13.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}
