# Shared storage VM (M006, ADR-012): user data of k3s applications lives here, outside the k3s cluster, on
# pve-core's NVMe thin pool, exported over NFS to the k3s nodes only. Single failure domain (one host, one
# disk) until dedicated NAS storage or Ceph exists. The data disk is protected: prevent_destroy.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_download_file" "debian" {
  node_name    = var.profile.node
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # Own copy: the same image on pve-core belongs to the deploy-runner root; two states must not own one file.
  file_name          = "storage-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "storage" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  description         = "Shared NFS storage for k3s user data (homelab-iac terraform/stacks/storage, M006). Holds data: never recreate."
  tags                = ["terraform", "storage"]
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
  # Data disk (thin): grows by raising data_disk_gb; Ansible grows the filesystem.
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi1"
    file_format  = "raw"
    size         = var.profile.data_disk_gb
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
    prevent_destroy = true
    ignore_changes  = [started]
  }
}
