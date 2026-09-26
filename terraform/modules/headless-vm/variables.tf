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
    error_message = "Supply the repository-managed Ed25519 public key, never a private key."
  }
}
