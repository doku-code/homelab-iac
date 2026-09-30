provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = var.proxmox_insecure
}

provider "proxmox" {
  alias     = "root"
  endpoint  = var.proxmox_endpoint
  insecure  = var.proxmox_insecure
  username  = "root@pam"
  api_token = ""
  # Password comes only from PROXMOX_VE_PASSWORD via the scoped runtime wrapper.
}

locals {
  nodes = {
    ts-router-01 = "pve-k8s-01"
    ts-router-02 = "pve-k8s-02"
  }
}

resource "proxmox_virtual_environment_container" "router" {
  provider = proxmox.root
  for_each = var.routers

  node_name     = local.nodes[each.key]
  vm_id         = each.value.vm_id
  description   = "Independent Tailscale subnet router; managed by homelab-iac"
  tags          = ["terraform", "tailscale", "subnet-router"]
  unprivileged  = true
  started       = true
  start_on_boot = true

  features {
    nesting = false
    fuse    = false
    keyctl  = false
    mknod   = false
    mount   = []
  }
  cpu {
    cores = 1
  }
  memory {
    dedicated = 512
    swap      = 256
  }
  disk {
    datastore_id = each.value.datastore_id
    size         = 8
  }
  # Proxmox devN API: no privileged CT or host configuration edits.
  device_passthrough {
    path = "/dev/net/tun"
    mode = "0666"
    uid  = 0
    gid  = 0
  }
  network_interface {
    name     = "eth0"
    bridge   = each.value.bridge
    firewall = true
  }
  initialization {
    hostname = each.key
    dns {
      domain  = "home.arpa"
      servers = ["192.168.0.20"]
    }
    ip_config {
      ipv4 {
        address = each.value.ipv4_address
        gateway = "192.168.0.1"
      }
    }
    user_account {
      keys = [trimspace(var.management_ssh_public_key != null ? var.management_ssh_public_key : file("${path.module}/../../../keys/doku-lab-admin.pub"))]
    }
  }
  operating_system {
    template_file_id = each.value.template_file_id
    type             = "debian"
  }
  lifecycle {
    prevent_destroy = true
  }
}

output "ansible_inventory" {
  description = "Only these two managed guests; no host or existing-router target"
  value = {
    tailscale_routers = {
      hosts = { for name, router in proxmox_virtual_environment_container.router : name => {
        ansible_host            = split("/", router.initialization[0].ip_config[0].ipv4[0].address)[0]
        ansible_user            = "root"
        ansible_ssh_common_args = "-o StrictHostKeyChecking=yes"
      } }
    }
  }
}
