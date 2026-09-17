variable "proxmox_endpoint" {
  description = "Proxmox VE API endpoint"
  type        = string
}

variable "proxmox_insecure" {
  description = "Whether to skip Proxmox API certificate verification"
  type        = bool
  default     = false
}

variable "vm_id" {
  description = "Existing Forgejo runner container VMID"
  type        = number
}

variable "unprivileged" {
  description = "Existing container's unprivileged setting"
  type        = bool
}

variable "rootfs_datastore_id" {
  description = "Existing container root filesystem datastore"
  type        = string
}

variable "rootfs_size" {
  description = "Existing container root filesystem size in GiB"
  type        = number
}

variable "operating_system_template_file_id" {
  description = "Existing container OS template file ID"
  type        = string
}

variable "network_bridge" {
  description = "Existing container network bridge"
  type        = string
}

variable "network_mac_address" {
  description = "Existing container network MAC address"
  type        = string
}

variable "network_firewall" {
  description = "Existing container network firewall setting"
  type        = bool
}

variable "network_ipv4_address" {
  description = "Existing container IPv4 address in CIDR notation"
  type        = string
}

variable "network_ipv4_gateway" {
  description = "Existing container IPv4 gateway"
  type        = string
}

variable "dns_servers" {
  description = "Existing container DNS servers"
  type        = list(string)
}

variable "cpu_cores" {
  description = "Existing container CPU core allocation"
  type        = number
}

variable "memory_mib" {
  description = "Existing container memory allocation in MiB"
  type        = number
}

variable "swap_mib" {
  description = "Existing container swap allocation in MiB"
  type        = number
  default     = 0
}

variable "features" {
  description = "Existing container feature flags"
  type = object({
    nesting = bool
    fuse    = bool
    keyctl  = bool
    mknod   = bool
    mount   = list(string)
  })
}

variable "tags" {
  description = "Existing container tags"
  type        = set(string)
}

variable "started" {
  description = "Whether Terraform should keep the adopted container started"
  type        = bool
}

variable "on_boot" {
  description = "Whether the adopted container starts on host boot"
  type        = bool
}
