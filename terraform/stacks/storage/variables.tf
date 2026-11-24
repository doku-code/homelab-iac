variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "profile" {
  description = "Storage VM allocation."
  type = object({
    node         = string
    vm_id        = number
    name         = string
    ipv4         = string
    cores        = number
    memory       = number
    os_disk_gb   = number
    data_disk_gb = number
  })
  validation {
    condition     = contains(["pve-core", "pve-compute"], var.profile.node)
    error_message = "The shared storage VM lives on pve-compute (its 2 TB NVMe, storage lab-vms; operator decision 2026-11-24) or on pve-core, where it was built."
  }
  validation {
    condition     = var.profile.vm_id >= 350 && var.profile.vm_id <= 359 && can(regex("^192\\.168\\.0\\.5[0-9]/24$", var.profile.ipv4))
    error_message = "Storage VMs use VMIDs 350-359 and static 192.168.0.50-59/24."
  }
  validation {
    condition     = var.profile.cores >= 1 && var.profile.memory >= 1024 && var.profile.os_disk_gb >= 10 && var.profile.data_disk_gb >= 50 && var.profile.data_disk_gb <= 700
    error_message = "Need >= 1 core, 1024 MiB, 10 GiB OS disk and a 50-700 GiB data disk (thin; lab-vms on pve-compute is 1.8 TiB)."
  }
}

variable "image_datastore" {
  type    = string
  default = "local"
}

variable "disk_datastore" {
  description = "Storage of the two disks and of the cloud-init drive. lab-vms exists on pve-compute only."
  type        = string
  default     = "local-lvm"
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
  type    = list(string)
  default = ["192.168.0.20"]
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
