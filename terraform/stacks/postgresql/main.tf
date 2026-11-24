# Shared PostgreSQL platform (M007, ADR-015): three Patroni VMs outside the k3s cluster, one per Proxmox
# host, each with its own data disk. Every application database lives here. The VMs hold data:
# prevent_destroy; a broken replica is re-initialised by Patroni, not recreated.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

locals {
  proxmox_nodes = toset([for n in values(var.nodes) : n.node])
}

resource "proxmox_download_file" "debian" {
  for_each     = local.proxmox_nodes
  node_name    = each.key
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # Own copy: the same image on these hosts belongs to other roots; two states must not own one file.
  file_name          = "postgresql-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "node" {
  for_each            = var.nodes
  node_name           = each.value.node
  vm_id               = each.value.vm_id
  name                = each.key
  description         = "PostgreSQL/Patroni member (homelab-iac terraform/stacks/postgresql, M007). Holds data: never recreate."
  tags                = ["terraform", "postgresql"]
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
    cores = each.value.cores
    type  = "x86-64-v2-AES"
  }
  memory {
    dedicated = each.value.memory
  }
  # OS disk from the cloud image (etcd lives here).
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    import_from  = proxmox_download_file.debian[each.value.node].id
    size         = each.value.os_disk_gb
    discard      = "on"
    ssd          = true
    iothread     = true
  }
  # PostgreSQL data disk (thin): grows by raising data_disk_gb; Ansible grows the filesystem.
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi1"
    file_format  = "raw"
    size         = each.value.data_disk_gb
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
        address = each.value.ipv4
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
    # The image is only read when the VM is created. A VM moved to another node (live migration) must not be
    # touched because its image copy now comes from that node.
    ignore_changes = [started, disk[0].import_from]
  }
}
