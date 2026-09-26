variable "proxmox_endpoint" {
  type = string
}

variable "proxmox_insecure" {
  type    = bool
  default = false
}

variable "image" {
  description = "Reviewed versioned Debian 13 AMD64 cloud image; no mutable/latest URL."
  type = object({
    url    = string
    sha256 = string
  })
  nullable = false
  validation {
    condition = (
      can(regex("^https://[^[:space:]]+$", var.image.url)) &&
      !strcontains(lower(var.image.url), "latest") &&
      can(regex("[0-9]{8}", var.image.url)) &&
      can(regex("^[a-f0-9]{64}$", var.image.sha256))
    )
    error_message = "Use a dated HTTPS Debian image URL and its verified SHA256."
  }
}

variable "servers" {
  description = "Three reviewed allocations; no live IDs/IPs. Confirm datastore locality during preflight."
  type = map(object({
    node            = string
    vm_id           = number
    name            = string
    image_datastore = string
    disk_datastore  = string
    storage_local   = bool
    bridge          = string
    ipv4            = string
    gateway         = string
    dns_servers     = list(string)
    cores           = optional(number, 2)
    memory          = optional(number, 4096)
    disk_gb         = optional(number, 32)
  }))
  nullable = false
  validation {
    condition     = toset(keys(var.servers)) == toset(["server-1", "server-2", "server-3"])
    error_message = "Declare exactly server-1, server-2 and server-3; no implicit live allocation."
  }
  validation {
    condition = (
      length(distinct([for p in values(var.servers) : p.vm_id])) == 3 &&
      length(distinct([for p in values(var.servers) : split("/", p.ipv4)[0]])) == 3 &&
      length(distinct([for p in values(var.servers) : lower(p.name)])) == 3
    )
    error_message = "VMIDs, IP addresses and hostnames must be unique."
  }
  validation {
    condition = alltrue([for p in values(var.servers) : try(
      p.vm_id >= 100 && p.vm_id <= 999999999 && p.vm_id == floor(p.vm_id) &&
      p.cores >= 2 && p.cores == floor(p.cores) &&
      p.memory >= 4096 && p.memory == floor(p.memory) &&
      p.disk_gb >= 32 && p.disk_gb == floor(p.disk_gb) && p.storage_local &&
      alltrue([for s in [p.node, p.image_datastore, p.disk_datastore, p.bridge] : can(regex("^[a-zA-Z0-9][a-zA-Z0-9_-]*$", s))]) &&
      can(regex("^[a-z][a-z0-9-]{0,61}[a-z0-9]$", p.name)) &&
      can(cidrnetmask(p.ipv4)) && !endswith(p.ipv4, "/32") &&
      can(cidrnetmask("${p.gateway}/32")) &&
      cidrhost("${p.gateway}/${split("/", p.ipv4)[1]}", 0) == cidrhost(p.ipv4, 0) &&
      split("/", p.ipv4)[0] != p.gateway &&
      split("/", p.ipv4)[0] != cidrhost(p.ipv4, 0) &&
      split("/", p.ipv4)[0] != cidrhost(p.ipv4, -1) &&
      length(p.dns_servers) > 0 && alltrue([for ip in p.dns_servers : can(cidrnetmask("${ip}/32"))]), false
    )])
    error_message = "Require valid allocation/network, local storage intent and at least 2 CPU, 4096 MiB RAM, 32 GiB disk per node. Verify real storage/capacity separately."
  }
}
