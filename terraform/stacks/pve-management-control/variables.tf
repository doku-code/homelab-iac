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

variable "desktop_iso" {
  description = "Official Ubuntu Desktop ISO, pinned by SHA256 from the release SHA256SUMS."
  type = object({
    url    = string
    sha256 = string
  })
  validation {
    condition     = can(regex("^https://releases\\.ubuntu\\.com/.+-desktop-amd64\\.iso$", var.desktop_iso.url)) && can(regex("^[0-9a-f]{64}$", var.desktop_iso.sha256))
    error_message = "Use an https://releases.ubuntu.com/ desktop-amd64 ISO and its 64-hex SHA256."
  }
}

variable "autoinstall_seed_url" {
  description = "NoCloud seed served by `make mgmt-autoinstall-serve` on the operator workstation (trailing slash)."
  type        = string
  validation {
    condition     = can(regex("^http://[0-9.]+:[0-9]+/$", var.autoinstall_seed_url))
    error_message = "Use http://<workstation IPv4>:<port>/ with a trailing slash."
  }
}

variable "workstation_enabled" {
  description = "false only while a previous VM with the same VMID is removed (two-step reinstall); prevent_destroy still guards this VM."
  type        = bool
  default     = true
}

variable "desktop" {
  description = "Installer choices for the desktop: locale, keyboard and time zone."
  type = object({
    locale          = string
    keyboard_layout = string
    timezone        = string
  })
  default = {
    locale          = "fr_CA.UTF-8"
    keyboard_layout = "ca"
    timezone        = "America/Toronto"
  }
}

variable "admin_username" {
  description = "Administrative (desktop) user created by the installer."
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "Ed25519 public key for the administrative user; defaults to the repository operator key."
  type        = string
  default     = null
}
