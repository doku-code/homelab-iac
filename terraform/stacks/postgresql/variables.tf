variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "nodes" {
  description = "Patroni members by name. failover_priority: higher is preferred as the new primary; 0 never becomes primary."
  type = map(object({
    node              = string
    vm_id             = number
    ipv4              = string
    cores             = number
    memory            = number
    os_disk_gb        = number
    data_disk_gb      = number
    failover_priority = optional(number, 1)
  }))
  validation {
    condition     = length(var.nodes) == 3 && length(distinct([for n in values(var.nodes) : n.node])) == 3
    error_message = "Exactly three members on three different Proxmox hosts (etcd quorum survives one host)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : contains(["pve-core", "pve-infra", "pve-lab"], n.node)])
    error_message = "PostgreSQL VMs run on pve-core, pve-infra or pve-lab (new cluster)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.vm_id >= 360 && n.vm_id <= 369 && can(regex("^192\\.168\\.0\\.6[1-9]/24$", n.ipv4))])
    error_message = "PostgreSQL VMs use VMIDs 360-369 and static 192.168.0.61-69/24 (.60 is the virtual IP)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.cores >= 2 && n.memory >= 2048 && n.os_disk_gb >= 10 && n.data_disk_gb >= 20 && n.data_disk_gb <= 150])
    error_message = "Members need >= 2 cores, 2048 MiB, a 10 GiB OS disk and a 20-150 GiB data disk (pve-infra's pool is 170 GiB)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.failover_priority >= 0 && n.failover_priority <= 10])
    error_message = "failover_priority is 0-10."
  }
  validation {
    condition     = length(distinct([for n in values(var.nodes) : n.vm_id])) == 3 && length(distinct([for n in values(var.nodes) : n.ipv4])) == 3
    error_message = "VMIDs and addresses must be unique."
  }
}

variable "virtual_ip" {
  description = "Address applications connect to; held by the current primary (vip-manager)."
  type        = string
  default     = "192.168.0.60"
  validation {
    condition     = var.virtual_ip == "192.168.0.60"
    error_message = "The PostgreSQL virtual IP is 192.168.0.60 (reserved with the .60-.69 range)."
  }
}

variable "image_datastore" {
  description = "Directory storage with the import content type on every hosting node."
  type        = string
  default     = "local"
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
