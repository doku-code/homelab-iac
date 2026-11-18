# DNS VM (TASK-022): AdGuard Home for the LAN, rebuilt from code. Outside k3s on purpose: the k3s nodes resolve
# through it (image pulls), so it must start without the cluster, and it needs port 53 on a fixed address.
# The VM is rebuildable (its configuration is in Git, its query log is not kept): no prevent_destroy.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_download_file" "debian" {
  node_name    = var.profile.node
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # Own copy: a file on a node has one owner (the postgresql root has its copy on the same node).
  file_name          = "dns-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "dns" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  description         = "AdGuard Home, LAN DNS (homelab-iac terraform/stacks/dns, TASK-022). Rebuildable from Git."
  tags                = ["terraform", "dns"]
  started             = true
  on_boot             = true
  reboot_after_update = false
  machine             = "q35"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  agent {
    enabled = true
    timeout = "2m"
  }
  cpu {
    cores = var.profile.cores
    type  = "x86-64-v2-AES"
  }
  memory {
    dedicated = var.profile.memory
  }
  # OS disk from the cloud image.
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    import_from  = proxmox_download_file.debian.id
    size         = var.profile.os_disk_gb
    discard      = "on"
    ssd          = true
    iothread     = true
  }
  network_device {
    bridge   = var.bridge
    model    = "virtio"
    firewall = true
  }
  initialization {
    datastore_id = var.disk_datastore
    ip_config {
      ipv4 {
        address = var.profile.ipv4
        gateway = var.gateway
      }
    }
    dns {
      servers = var.dns_servers
    }
    user_account {
      username = var.admin_username
      keys     = [trimspace(coalesce(var.ssh_public_key, file("${path.module}/../../../keys/mgmt-control-01.pub")))]
    }
  }
  operating_system {
    type = "l26"
  }
  lifecycle {
    ignore_changes = [started]
  }
}
