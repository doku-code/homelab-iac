variable "proxmox_endpoint" {
  description = "doku-lab cluster API endpoint (pve-management .10 or pve-core .11). TLS is always verified."
  type        = string
  validation {
    condition     = can(regex("^https://192\\.168\\.0\\.(10|11):8006/$", var.proxmox_endpoint)) || can(regex("\\.invalid:8006/$", var.proxmox_endpoint))
    error_message = "Use https://192.168.0.10:8006/ or https://192.168.0.11:8006/ (new cluster, by IP); never the old environment."
  }
}

variable "nodes" {
  description = "k3s VMs by name. role: server (embedded etcd member) or agent."
  type = map(object({
    node    = string
    vm_id   = number
    role    = string
    ipv4    = string
    cores   = number
    memory  = number
    disk_gb = number
  }))
  validation {
    condition     = length([for n in values(var.nodes) : n if n.role == "server"]) >= 1
    error_message = "At least one k3s server is required."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : contains(["pve-core", "pve-infra", "pve-lab", "pve-compute"], n.node)])
    error_message = "k3s VMs run on pve-core, pve-infra, pve-lab or pve-compute; pve-management hosts the workstation."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : contains(["server", "agent"], n.role)])
    error_message = "role must be server or agent."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.vm_id >= 310 && n.vm_id <= 349])
    error_message = "k3s VMIDs are 310-349 (9000+ is reserved for disposable CI guests)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : can(regex("^192\\.168\\.0\\.(4[0-9])/24$", n.ipv4))])
    error_message = "k3s addresses are static 192.168.0.40-49/24 (outside the DHCP pool .100-.200)."
  }
  validation {
    condition     = alltrue([for n in values(var.nodes) : n.cores >= 2 && n.memory >= 4096 && n.disk_gb >= 32])
    error_message = "k3s nodes need >= 2 cores, 4096 MiB and 32 GiB."
  }
  validation {
    condition     = length(distinct([for n in values(var.nodes) : n.vm_id])) == length(var.nodes) && length(distinct([for n in values(var.nodes) : n.ipv4])) == length(var.nodes)
    error_message = "VMIDs and addresses must be unique."
  }
}

variable "image_datastore" {
  description = "Directory storage with the import content type on every hosting node."
  type        = string
  default     = "local"
}

variable "disk_datastore" {
  type    = string
  default = "local-lvm"
}

variable "bridge" {
  type    = string
  default = "vmbr0"
}

variable "gateway" {
  type    = string
  default = "192.168.0.1"
}

variable "dns_servers" {
  type    = list(string)
  default = ["192.168.0.20"]
}

variable "image" {
  description = "Dated Debian 13 generic cloud image and its SHA512 from the release SHA512SUMS."
  type = object({
    url    = string
    sha512 = string
  })
  validation {
    condition = (
      can(regex("^https://cloud\\.debian\\.org/images/cloud/trixie/[0-9]{8}-[0-9]+/debian-13-genericcloud-amd64-[0-9]{8}-[0-9]+\\.qcow2$", var.image.url)) &&
      can(regex("^[0-9a-f]{128}$", var.image.sha512))
    )
    error_message = "Use a dated cloud.debian.org trixie genericcloud-amd64 qcow2 and its 128-hex SHA512."
  }
}

variable "admin_username" {
  type    = string
  default = "debian"
}

variable "ssh_public_key" {
  description = "Ed25519 public key for the admin user; defaults to the workstation key (keys/mgmt-control-01.pub)."
  type        = string
  default     = null
}
