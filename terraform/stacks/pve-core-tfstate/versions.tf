terraform {
  required_version = ">= 1.16.0"

  # This host must be recoverable without its PostgreSQL service.
  backend "local" {}

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}
