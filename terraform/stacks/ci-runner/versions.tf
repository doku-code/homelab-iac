# OpenTofu root (ADR-003): run it with `tofu`, through the ci-runner-* Make targets.
# Local state on the operator workstation only (ADR-008), like pve-management-control and deploy-runner.
terraform {
  required_version = ">= 1.13.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}
