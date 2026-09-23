terraform {
  required_version = ">= 1.16.0"

  # Garage must not depend on its own S3 service for bootstrap state.
  backend "local" {}

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}
