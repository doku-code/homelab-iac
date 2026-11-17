# OpenTofu root applied ONLY by the deployment runner through /usr/local/sbin/homelab-deploy (ADR-014).
# Local state on the runner (/var/lib/homelab-deploy/state), path passed at init: one writer, the runner.
terraform {
  required_version = ">= 1.13.0"
  backend "local" {}
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}
