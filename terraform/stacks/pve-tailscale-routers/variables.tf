variable "proxmox_endpoint" {
  description = "Existing cluster API endpoint; credentials come only from the provider environment"
  type        = string
  default     = "https://192.168.0.11:8006/"
}

variable "proxmox_insecure" {
  description = "Explicit opt-in to the existing internal-certificate convention; prefer trusted CA verification"
  type        = bool
  default     = false
}

variable "management_ssh_public_key" {
  description = "Optional external public key; null uses the tracked administration public key"
  type        = string
  default     = null
  validation {
    condition     = var.management_ssh_public_key == null ? true : can(regex("^ssh-ed25519 [A-Za-z0-9+/=]+", trimspace(var.management_ssh_public_key)))
    error_message = "Supply an Ed25519 public key, never a private key."
  }
}

variable "routers" {
  description = "Operator-approved allocations and node-local storage/template IDs; no inferred free VMIDs or IPs"
  type = map(object({
    vm_id            = number
    ipv4_address     = string
    datastore_id     = string
    template_file_id = string
    bridge           = optional(string, "vmbr0")
  }))
  validation {
    condition     = toset(keys(var.routers)) == toset(["ts-router-01", "ts-router-02"])
    error_message = "Provide exactly ts-router-01 and ts-router-02."
  }
  validation {
    condition = (
      length(distinct([for r in var.routers : r.vm_id])) == 2 &&
      alltrue([for r in var.routers : r.vm_id >= 100 && r.vm_id <= 999999999 && floor(r.vm_id) == r.vm_id])
    )
    error_message = "Supply two distinct, cluster-wide free, operator-approved VMIDs."
  }
  validation {
    condition = (
      length(distinct([for r in var.routers : r.ipv4_address])) == 2 &&
      alltrue([for r in var.routers : can(regex("^192\\.168\\.0\\.([2-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-4])/24$", r.ipv4_address))])
    )
    error_message = "Supply two distinct approved LAN host addresses in 192.168.0.0/24; not the gateway."
  }
  validation {
    condition = alltrue([for r in var.routers :
      length(trimspace(r.datastore_id)) > 0 && length(trimspace(r.bridge)) > 0 &&
      can(regex("^[^:]+:vztmpl/debian-13-standard_[^/]+_amd64.tar.zst$", r.template_file_id))
    ])
    error_message = "Confirm storage/bridge and an existing Debian 13 amd64 template accessible on each target node."
  }
}
