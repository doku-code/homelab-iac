variable "proxmox_endpoint" {
  type = string
}

variable "proxmox_insecure" {
  type    = bool
  default = false
}

variable "profile" {
  description = "Explicit reviewed allocation and pinned Debian 13 cloud image. No live defaults."
  type = object({
    node            = string
    vm_id           = number
    name            = string
    image_datastore = string
    disk_datastore  = string
    image_url       = string
    image_sha256    = string
    bridge          = string
    ipv4            = string
    gateway         = string
    dns_servers     = list(string)
    cores           = number
    memory          = number
    disk_gb         = number
  })
  nullable = false
  validation {
    condition = try(
      var.profile.vm_id >= 100 && var.profile.vm_id == floor(var.profile.vm_id) &&
      var.profile.cores >= 1 && var.profile.cores == floor(var.profile.cores) &&
      var.profile.memory >= 2048 && var.profile.disk_gb >= 16 &&
      alltrue([for value in [var.profile.node, var.profile.name, var.profile.image_datastore, var.profile.disk_datastore, var.profile.bridge] : length(trimspace(value)) > 0]) &&
      can(regex("^https://", var.profile.image_url)) && !strcontains(var.profile.image_url, "/latest/") &&
      can(regex("^[a-f0-9]{64}$", var.profile.image_sha256)) &&
      can(cidrnetmask(var.profile.ipv4)) && can(cidrnetmask("${var.profile.gateway}/32")) &&
      length(var.profile.dns_servers) > 0 && alltrue([for ip in var.profile.dns_servers : can(cidrnetmask("${ip}/32"))]),
      false
    )
    error_message = "Provide an explicit integer VMID, sizing, storage/bridge, IPv4/CIDR/gateway/DNS and versioned HTTPS image with SHA256; allocation still needs live approval."
  }
}
