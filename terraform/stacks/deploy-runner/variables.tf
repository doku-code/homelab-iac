variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "profile" {
  description = "Runner VM allocation, confirmed by read-only discovery and the operator."
  type = object({
    node            = string
    vm_id           = number
    name            = string
    image_datastore = string
    disk_datastore  = string
    bridge          = string
    ipv4            = string
    gateway         = string
    dns_servers     = list(string)
    cores           = number
    memory          = number
    disk_gb         = number
  })
  validation {
    condition     = contains(["pve-management", "pve-core"], var.profile.node)
    error_message = "The bootstrap runner lives on pve-core (operator decision 2026-11-17) or pve-management."
  }
  validation {
    condition     = can(cidrhost(var.profile.ipv4, 0)) && can(regex("^[0-9.]+/[0-9]+$", var.profile.ipv4))
    error_message = "Use a static IPv4 address in CIDR form."
  }
  validation {
    condition     = var.profile.vm_id >= 100 && var.profile.vm_id < 9000 && var.profile.cores >= 1 && var.profile.memory >= 1024 && var.profile.disk_gb >= 10
    error_message = "Use a VMID 100-8999 (9000+ is reserved for disposable CI guests), >= 1 core, 1024 MiB, 10 GiB."
  }
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
  description = "Cloud-init administrative user (Ansible connects as this user)."
  type        = string
  default     = "debian"
}

variable "ssh_public_key" {
  description = "Ed25519 public key for the admin user; defaults to the workstation key (keys/mgmt-control-01.pub)."
  type        = string
  default     = null
}
