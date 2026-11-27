variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "profile" {
  description = "Media VM allocation. gpu_mapping: the Proxmox PCI resource mapping handed to the VM (null: none)."
  type = object({
    node         = string
    vm_id        = number
    name         = string
    ipv4         = string
    cores        = number
    memory       = number
    os_disk_gb   = number
    data_disk_gb = number
    gpu_mapping  = optional(string)
  })
  validation {
    condition     = contains(["pve-infra", "pve-lab"], var.profile.node)
    error_message = "The media VM runs on pve-infra (operator's choice) or on pve-lab, the holding node."
  }
  validation {
    condition     = var.profile.vm_id >= 380 && var.profile.vm_id <= 389 && can(regex("^192\\.168\\.0\\.8[0-9]/24$", var.profile.ipv4))
    error_message = "Media VMs use VMIDs 380-389 and static 192.168.0.80-89/24."
  }
  validation {
    condition     = var.profile.cores >= 2 && var.profile.memory >= 4096 && var.profile.os_disk_gb >= 12 && var.profile.data_disk_gb >= 40
    error_message = "Need >= 2 cores, 4096 MiB, a 12 GiB system disk and a 40 GiB data disk."
  }
  validation {
    condition     = var.profile.gpu_mapping == null || can(regex("^[a-z][a-z0-9-]*$", coalesce(var.profile.gpu_mapping, "x")))
    error_message = "gpu_mapping is the name of a Proxmox PCI resource mapping, never a device address."
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
  description = "Resolvers of the VM: the LAN DNS (the *.doku-lab.net names) with a public one behind it."
  type        = list(string)
  default     = ["192.168.0.20", "9.9.9.9"]
}

variable "image" {
  description = "Dated Debian 13 generic cloud image and its SHA512 from the release SHA512SUMS. The generic image, not genericcloud: its kernel has the graphics driver (i915) the hardware transcoding needs."
  type = object({
    url    = string
    sha512 = string
  })
  validation {
    condition = (
      can(regex("^https://cloud\\.debian\\.org/images/cloud/trixie/[0-9]{8}-[0-9]+/debian-13-generic-amd64-[0-9]{8}-[0-9]+\\.qcow2$", var.image.url)) &&
      can(regex("^[0-9a-f]{128}$", var.image.sha512))
    )
    error_message = "Use a dated cloud.debian.org trixie generic-amd64 qcow2 and its 128-hex SHA512."
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

variable "node" {
  description = "Node of the containers: pve-infra (operator's choice; it has the graphics adapter Jellyfin transcodes with)."
  type        = string
  default     = "pve-infra"
  validation {
    condition     = contains(["pve-infra", "pve-lab"], var.node)
    error_message = "The media containers run on pve-infra or on pve-lab, the holding node."
  }
}

variable "containers" {
  description = "One container per media service: name, VMID, address and size. memory and swap in MiB, disk_gb for the system and the service's own data."
  type = map(object({
    vm_id   = number
    ipv4    = string
    cores   = number
    memory  = number
    swap    = number
    disk_gb = number
  }))
  validation {
    condition     = alltrue([for name, c in var.containers : contains(["jellyfin", "seerr", "radarr", "sonarr", "prowlarr"], name)])
    error_message = "Known services: jellyfin, seerr, radarr, sonarr, prowlarr. qBittorrent stays on the NAS."
  }
  validation {
    condition     = alltrue([for c in values(var.containers) : c.vm_id >= 381 && c.vm_id <= 389 && can(regex("^192\\.168\\.0\\.8[1-9]/24$", c.ipv4))])
    error_message = "Media containers use VMIDs 381-389 and static 192.168.0.81-89/24."
  }
  validation {
    condition     = length(distinct([for c in values(var.containers) : c.vm_id])) == length(var.containers) && length(distinct([for c in values(var.containers) : c.ipv4])) == length(var.containers)
    error_message = "One VMID and one address per container."
  }
  validation {
    condition     = alltrue([for c in values(var.containers) : c.cores >= 1 && c.memory >= 512 && c.disk_gb >= 6])
    error_message = "Need >= 1 core, 512 MiB and a 6 GiB disk per container."
  }
}

variable "template" {
  description = "Debian 13 container template from download.proxmox.com and its SHA512 (pveam's index)."
  type = object({
    url    = string
    sha512 = string
  })
  validation {
    condition     = can(regex("^http://download\\.proxmox\\.com/images/system/debian-13-standard_[0-9.]+-[0-9]+_amd64\\.tar\\.zst$", var.template.url)) && can(regex("^[0-9a-f]{128}$", var.template.sha512))
    error_message = "Use a debian-13-standard amd64 template of download.proxmox.com and its 128-hex SHA512."
  }
}
