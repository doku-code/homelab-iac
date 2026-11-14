variable "profile" {
  type = object({
    node           = string
    vm_id          = number
    name           = string
    disk_datastore = string
    bridge         = string
    ipv4           = string
    gateway        = string
    dns_servers    = list(string)
    cores          = number
    memory         = number
    disk_gb        = number
  })
}

variable "image_id" {
  type = string
}

variable "tags" {
  type    = list(string)
  default = []
}

variable "ssh_public_key" {
  type = string
  validation {
    condition     = startswith(trimspace(var.ssh_public_key), "ssh-ed25519 ")
    error_message = "Supply an Ed25519 public key, never a private key."
  }
}

# Defaults preserve the legacy Debian, stopped-by-default behaviour of existing roots.
variable "username" {
  type    = string
  default = "debian"
}

variable "started" {
  type    = bool
  default = false
}

variable "on_boot" {
  type    = bool
  default = false
}

# Thin-pool space reclaim: "on" passes guest TRIM through. Defaults match the provider defaults,
# so existing roots plan unchanged.
variable "disk_discard" {
  type    = string
  default = "ignore"
  validation {
    condition     = contains(["on", "ignore"], var.disk_discard)
    error_message = "disk_discard must be \"on\" or \"ignore\"."
  }
}

variable "disk_ssd" {
  type    = bool
  default = false
}

variable "cpu_type" {
  description = "QEMU CPU model. x86-64-v2-AES keeps guests migratable; standalone hosts may use host."
  type        = string
  default     = "x86-64-v2-AES"
}
