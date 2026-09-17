resource "proxmox_virtual_environment_container" "forgejo_runner" {
  node_name   = "pve-compute"
  vm_id       = var.vm_id
  description = "Forgejo Actions runner - adopted existing container"

  unprivileged  = var.unprivileged
  tags          = var.tags
  started       = var.started
  start_on_boot = var.on_boot

  features {
    nesting = var.features.nesting
    fuse    = var.features.fuse
    keyctl  = var.features.keyctl
    mknod   = var.features.mknod
    mount   = var.features.mount
  }

  cpu {
    cores = var.cpu_cores
  }

  memory {
    dedicated = var.memory_mib
    swap      = var.swap_mib
  }

  disk {
    datastore_id = var.rootfs_datastore_id
    size         = var.rootfs_size
  }

  network_interface {
    name        = "eth0"
    bridge      = var.network_bridge
    firewall    = var.network_firewall
    mac_address = var.network_mac_address
  }

  initialization {
    hostname = "forgejo-runner"

    ip_config {
      ipv4 {
        address = var.network_ipv4_address
        gateway = var.network_ipv4_gateway
      }
    }

    dns {
      servers = var.dns_servers
    }
  }

  operating_system {
    template_file_id = var.operating_system_template_file_id
  }

  lifecycle {
    prevent_destroy = true
  }
}
