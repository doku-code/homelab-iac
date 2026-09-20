resource "proxmox_virtual_environment_container" "forgejo_runner_migration" {
  node_name = "pve-compute"
  vm_id     = 301

  unprivileged  = true
  tags          = ["terraform", "forgejo-runner", "migration"]
  started       = true
  start_on_boot = true

  features {
    nesting = true
    fuse    = false
    keyctl  = false
    mknod   = false
    mount   = []
  }

  cpu {
    cores = 4
  }

  memory {
    dedicated = 6144
    swap      = 512
  }

  disk {
    datastore_id = "local-lvm"
    size         = 38
  }

  network_interface {
    name     = "eth0"
    bridge   = "vmbr0"
    firewall = true
  }

  initialization {
    hostname = "forgejo-runner-migration"

    dns {
      servers = var.dns_servers
    }

    ip_config {
      ipv4 {
        address = "192.168.0.31/24"
        gateway = "192.168.0.1"
      }

      ipv6 {
        address = "dhcp"
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

  console {
    enabled   = true
    tty_count = 2
    type      = "tty"
  }

  lifecycle {
    prevent_destroy = true
  }
}
