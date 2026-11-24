# No required_version here: each root pins its engine (Terraform for legacy roots, OpenTofu for new ones).
terraform {
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
  started             = var.started
  on_boot             = var.on_boot
  reboot_after_update = false
  machine             = "q35"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  agent {
    enabled = true
  }
  cpu {
    cores = var.profile.cores
    type  = var.cpu_type
  }
  memory {
    dedicated = var.profile.memory
  }
  disk {
    datastore_id = var.profile.disk_datastore
    interface    = "scsi0"
    import_from  = var.image_id
    size         = var.profile.disk_gb
    discard      = var.disk_discard
    ssd          = var.disk_ssd
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
      username = var.username
      keys     = [trimspace(var.ssh_public_key)]
    }
  }
  operating_system {
    type = "l26"
  }
  lifecycle {
    prevent_destroy = true
    # The image is only read when the VM is created. A VM moved to another node (live migration) must not be
    # touched because its image copy now comes from that node.
    ignore_changes = [started, disk[0].import_from]
  }
}

output "vm" {
  description = "Headless resource contract for parent outputs and mocked tests."
  value       = proxmox_virtual_environment_vm.this
}
