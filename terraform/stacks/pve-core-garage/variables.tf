variable "proxmox_endpoint" {
  description = "Proxmox VE API endpoint for pve-core"
  type        = string
  default     = "https://192.168.0.11:8006/"
}

variable "proxmox_insecure" {
  description = "Use the existing homelab internal Proxmox certificate convention"
  type        = bool
  default     = true
}

variable "management_ssh_public_key" {
  description = "Controller public key to seed root SSH access"
  type        = string

  validation {
    condition     = can(regex("^ssh-ed25519 [A-Za-z0-9+/=]+", trimspace(var.management_ssh_public_key)))
    error_message = "Supply the controller's Ed25519 public key, never its private key."
  }
}
