# CI runner (TASK-033): the Forgejo Actions runner that validates every repository. It runs code from any
# branch, so it never holds infrastructure credentials (ADR-008); deployments stay on deploy-runner-01 (ADR-014).
# The VM is rebuildable: its configuration is in Git, its registrations in the secret store, its caches are caches.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_download_file" "debian" {
  node_name    = var.profile.node
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # Own copy: a file on a node has one owner (the deploy-runner root has its copy on the same node).
  file_name          = "ci-runner-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "runner" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  description         = "Forgejo Actions validation runner (homelab-iac terraform/stacks/ci-runner, TASK-033). Holds no infrastructure credentials. Rebuildable from Git."
  tags                = ["ci-runner", "terraform"]
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
    # The image is only read when the VM is created. A VM moved to another node (live migration) must not be
    # touched because its image copy now comes from that node.
    ignore_changes = [started, disk[0].import_from]
  }
}
