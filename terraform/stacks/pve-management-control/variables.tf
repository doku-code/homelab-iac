variable "proxmox_endpoint" {
  description = "pve-management API endpoint. TLS is always verified (no insecure mode)."
  type        = string
  validation {
    condition     = can(regex("^https://[^/]+:8006/$", var.proxmox_endpoint))
    error_message = "Use https://<pve-management address or name>:8006/ (trailing slash required)."
  }
}

variable "profile" {
  description = "Management VM allocation. Every value must be confirmed by read-only discovery (make mgmt-discover)."
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
    condition     = var.profile.node == "pve-management"
    error_message = "This root only targets the standalone pve-management host."
  }
  validation {
    condition     = can(cidrhost(var.profile.ipv4, 0)) && can(regex("^[0-9.]+/[0-9]+$", var.profile.ipv4))
    error_message = "Use a static IPv4 address in CIDR form; DHCP is not accepted for the management VM."
  }
  validation {
    condition     = var.profile.vm_id >= 100 && var.profile.cores >= 1 && var.profile.memory >= 2048 && var.profile.disk_gb >= 20
    error_message = "Use a free VMID >= 100, at least 1 core, 2048 MiB RAM and 20 GiB disk."
  }
}

variable "image" {
  description = "Ubuntu LTS cloud image, pinned by SHA256 from the release SHA256SUMS."
  type = object({
    url    = string
    sha256 = string
  })
  validation {
    condition     = startswith(var.image.url, "https://cloud-images.ubuntu.com/") && can(regex("^[0-9a-f]{64}$", var.image.sha256))
    error_message = "Use an https://cloud-images.ubuntu.com/ image and its 64-hex SHA256."
  }
}

variable "admin_username" {
  description = "Cloud-init administrative user."
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "Ed25519 public key for the administrative user; defaults to the repository operator key."
  type        = string
  default     = null
}
