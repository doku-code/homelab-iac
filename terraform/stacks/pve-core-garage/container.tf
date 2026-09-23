resource "proxmox_virtual_environment_container" "garage" {
  node_name = "pve-core"
  vm_id     = 209

  unprivileged  = true
  tags          = ["terraform", "garage", "storage"]
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
    dedicated = 1024
    swap      = 512
  }

  disk {
    datastore_id = "local-lvm"
    size         = 16
  }

  network_interface {
    name     = "eth0"
    bridge   = "vmbr0"
    firewall = true
  }

  initialization {
    hostname = "garage"

    dns {
      domain  = "home.arpa"
      servers = ["192.168.0.20"]
    }

    ip_config {
      ipv4 {
        address = "192.168.0.29/24"
        gateway = "192.168.0.1"
      }
    }

    user_account {
      keys = [trimspace(var.management_ssh_public_key)]
    }
  }

  operating_system {
    template_file_id = "pve_library:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
    type             = "debian"
  }

  lifecycle {
    prevent_destroy = true
  }
}
