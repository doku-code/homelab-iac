variable "proxmox_endpoint" {
  description = "Proxmox VE API endpoint"
  type        = string
}

variable "proxmox_insecure" {
  description = "Whether to skip Proxmox API certificate verification"
  type        = bool
  default     = true
}

variable "management_ssh_public_key" {
  description = "Public key to seed root SSH access in the new container"
  type        = string

  validation {
    condition     = trimspace(var.management_ssh_public_key) != ""
    error_message = "management_ssh_public_key must be a non-empty public key."
  }
}

variable "dns_servers" {
  description = "DNS servers assigned during container initialization"
  type        = list(string)
  default     = ["192.168.0.20"]
}
