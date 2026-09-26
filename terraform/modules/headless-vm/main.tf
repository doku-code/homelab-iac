terraform {
  required_version = ">= 1.16.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.112.0"
    }
  }
}

resource "proxmox_virtual_environment_vm" "this" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  tags                = concat(["terraform"], var.tags)
  started             = false
  on_boot             = false
  reboot_after_update = false
  machine             = "q35"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  agent {
    enabled = true
  }
  cpu {
    cores = var.profile.cores
    type  = "x86-64-v2-AES"
  }
  memory {
    dedicated = var.profile.memory
  }
  disk {
    datastore_id = var.profile.disk_datastore
    interface    = "scsi0"
    import_from  = var.image_id
    size         = var.profile.disk_gb
  }
  network_device {
    bridge   = var.profile.bridge
    model    = "virtio"
    firewall = true
  }
  initialization {
    datastore_id = var.profile.disk_datastore
    ip_config {
      ipv4 {
        address = var.profile.ipv4
        gateway = var.profile.gateway
      }
    }
    dns {
      servers = var.profile.dns_servers
    }
    user_account {
      username = "debian"
      keys     = [trimspace(var.ssh_public_key)]
    }
  }
  operating_system {
    type = "l26"
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [started]
  }
}

output "vm" {
  description = "Headless resource contract for parent outputs and mocked tests."
  value       = proxmox_virtual_environment_vm.this
}
