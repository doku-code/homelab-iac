variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "profile" {
  description = "DNS VM allocation. ipv4 is the VM's own address; the service address 192.168.0.20 is added by Ansible at the cutover."
  type = object({
    node       = string
    vm_id      = number
    name       = string
    ipv4       = string
    cores      = number
    memory     = number
    os_disk_gb = number
  })
  validation {
    condition     = contains(["pve-core", "pve-infra", "pve-lab", "pve-compute"], var.profile.node)
    error_message = "The DNS VM runs on pve-core, pve-infra, pve-lab or pve-compute."
  }
  validation {
    condition     = var.profile.vm_id >= 370 && var.profile.vm_id <= 379 && can(regex("^192\\.168\\.0\\.7[0-9]/24$", var.profile.ipv4))
    error_message = "DNS VMs use VMIDs 370-379 and static 192.168.0.70-79/24."
  }
  validation {
    condition     = var.profile.cores >= 1 && var.profile.memory >= 1024 && var.profile.os_disk_gb >= 10
    error_message = "Need >= 1 core, 1024 MiB and a 10 GiB disk."
  }
}

variable "standby" {
  description = "Optional second DNS VM on another host; it shares the service address with the primary (keepalived)."
  type = object({
    node       = string
    vm_id      = number
    name       = string
    ipv4       = string
    cores      = number
    memory     = number
    os_disk_gb = number
  })
  default = null
  validation {
    condition     = var.standby == null || contains(["pve-core", "pve-infra", "pve-lab", "pve-compute"], try(var.standby.node, ""))
    error_message = "The standby DNS VM runs on pve-core, pve-infra, pve-lab or pve-compute."
  }
  validation {
    condition     = var.standby == null || (try(var.standby.vm_id, 0) >= 370 && try(var.standby.vm_id, 0) <= 379 && can(regex("^192\\.168\\.0\\.7[0-9]/24$", try(var.standby.ipv4, ""))))
    error_message = "DNS VMs use VMIDs 370-379 and static 192.168.0.70-79/24."
  }
  validation {
    condition     = var.standby == null || (try(var.standby.cores, 0) >= 1 && try(var.standby.memory, 0) >= 1024 && try(var.standby.os_disk_gb, 0) >= 10)
    error_message = "Need >= 1 core, 1024 MiB and a 10 GiB disk."
  }
  validation {
    condition = var.standby == null || (
      try(var.standby.node, "") != var.profile.node && try(var.standby.name, "") != var.profile.name &&
      try(var.standby.vm_id, 0) != var.profile.vm_id && try(var.standby.ipv4, "") != var.profile.ipv4
    )
    error_message = "The standby is another VM on another Proxmox host: that is its whole point."
  }
}

variable "image_datastore" {
  type    = string
  default = "local"
}

variable "disk_datastore" {
  type    = string
  default = "local-lvm"
}

variable "bridge" {
  type    = string
  default = "vmbr0"
}

variable "gateway" {
  type    = string
  default = "192.168.0.1"
}

variable "dns_servers" {
  description = "Resolvers of the VM itself: public ones, it cannot depend on the service it provides."
  type        = list(string)
  default     = ["9.9.9.9", "1.1.1.1"]
}

variable "image" {
  description = "Dated Debian 13 generic cloud image and its SHA512 from the release SHA512SUMS."
  type = object({
    url    = string
    sha512 = string
  })
  validation {
    condition = (
      can(regex("^https://cloud\\.debian\\.org/images/cloud/trixie/[0-9]{8}-[0-9]+/debian-13-genericcloud-amd64-[0-9]{8}-[0-9]+\\.qcow2$", var.image.url)) &&
      can(regex("^[0-9a-f]{128}$", var.image.sha512))
    )
    error_message = "Use a dated cloud.debian.org trixie genericcloud-amd64 qcow2 and its 128-hex SHA512."
  }
}

variable "admin_username" {
  type    = string
  default = "debian"
}

variable "ssh_public_key" {
  type    = string
  default = null
}
