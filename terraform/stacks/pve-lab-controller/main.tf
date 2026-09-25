provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = var.proxmox_insecure
}

# A small reusable Linux profile, not an adopted workstation or a cloned identity.
resource "proxmox_download_file" "linux" {
  node_name          = var.profile.node
  datastore_id       = var.profile.image_datastore
  content_type       = "import"
  url                = var.profile.image_url
  file_name          = "controller-${substr(var.profile.image_sha256, 0, 16)}.qcow2"
  checksum           = var.profile.image_sha256
  checksum_algorithm = "sha256"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "controller" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  tags                = ["terraform", "recovery-controller"]
  started             = false
  on_boot             = false
  reboot_after_update = false
  machine             = "q35"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
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
    import_from  = proxmox_download_file.linux.id
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
      keys     = [trimspace(file("${path.module}/../../../keys/doku-lab-admin.pub"))]
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
