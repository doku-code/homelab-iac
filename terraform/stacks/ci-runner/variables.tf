variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "profile" {
  description = "CI runner VM allocation."
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
    condition     = contains(["pve-management", "pve-core", "pve-infra", "pve-lab"], var.profile.node)
    error_message = "The CI runner runs on a node of the new cluster."
  }
  validation {
    condition     = var.profile.vm_id >= 303 && var.profile.vm_id <= 305 && can(regex("^192\\.168\\.0\\.3[3-5]/24$", var.profile.ipv4))
    error_message = "CI runners use VMIDs 303-305 and static 192.168.0.33-35/24 (302 and .32 are the deployment runner)."
  }
  validation {
    condition     = var.profile.cores >= 2 && var.profile.memory >= 4096 && var.profile.os_disk_gb >= 32
    error_message = "Need >= 2 cores, 4096 MiB and a 32 GiB disk (job images and caches live on it)."
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
  description = "LAN resolver: jobs pull images from git.doku-lab.net, a name only the LAN DNS answers."
  type        = list(string)
  default     = ["192.168.0.20"]
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
