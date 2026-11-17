variable "proxmox_endpoint" {
  type = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use the new cluster by IP (https://192.168.0.10:8006/ or .11); never the old environment."
  }
}

variable "node" {
  type    = string
  default = "pve-core"
  validation {
    condition     = contains(["pve-management", "pve-core"], var.node)
    error_message = "Disposable probes run on pve-management or pve-core."
  }
}

variable "vm_id" {
  type    = number
  default = 9900
  validation {
    condition     = var.vm_id >= 9900 && var.vm_id <= 9999
    error_message = "Disposable guests use VMIDs 9900-9999."
  }
}

variable "pool" {
  type    = string
  default = "ci-disposable"
  validation {
    condition     = var.pool == "ci-disposable"
    error_message = "Disposable guests live only in the ci-disposable pool (the runner token's scope)."
  }
}

variable "disk_datastore" {
  type    = string
  default = "local-lvm"
}
