terraform {
  required_version = ">= 1.16.0"
  backend "local" {}
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}

variable "ctid" {
  type = number
  validation {
    condition     = var.ctid >= 100 && var.ctid == floor(var.ctid)
    error_message = "Supply an approved free cluster-wide CTID."
  }
}

variable "proxmox_endpoint" {
  type    = string
  default = "https://192.168.0.11:8006/"
}

variable "proxmox_insecure" {
  type    = bool
  default = true
}

provider "proxmox" {
  alias     = "root"
  endpoint  = var.proxmox_endpoint
  insecure  = var.proxmox_insecure
  username  = "root@pam"
  api_token = ""
}

resource "proxmox_virtual_environment_container" "windmill" {
  provider      = proxmox.root
  node_name     = "pve-core"
  vm_id         = var.ctid
  unprivileged  = true
  started       = true
  start_on_boot = true
  tags          = ["terraform", "windmill"]

  features {
    nesting = true
    keyctl  = true
    fuse    = false
    mknod   = false
    mount   = []
  }
  cpu { cores = 2 }
  memory {
    dedicated = 4096
    swap      = 512
  }
  disk {
    datastore_id = "local-lvm"
    size         = 32
  }
  network_interface {
    name     = "eth0"
    bridge   = "vmbr0"
    firewall = true
  }
  initialization {
    hostname = "windmill"
    dns {
      domain  = "home.arpa"
      servers = ["192.168.0.20"]
    }
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
    user_account {
      keys = [trimspace(file("${path.module}/../../../keys/doku-lab-admin.pub"))]
    }
  }
  operating_system {
    template_file_id = "pve_library:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
    type             = "debian"
  }
  lifecycle { prevent_destroy = true }
}

output "ctid" { value = proxmox_virtual_environment_container.windmill.vm_id }
