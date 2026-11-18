# k3s cluster VMs (ADR-011, M004). One VM per k3s node from var.nodes; adding a server is a tfvars entry.
# Unlike the headless-vm module, these VMs are cattle: no prevent_destroy, so a node can be rebuilt from
# IaC (`-replace`). Cluster data never lives on these disks (ADR-012); etcd is rebuilt or rejoined.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

locals {
  proxmox_nodes = toset([for n in values(var.nodes) : n.node])
}

# Dated Debian 13 generic cloud image on every Proxmox node that hosts a k3s VM, verified by SHA512.
resource "proxmox_download_file" "debian" {
  for_each     = local.proxmox_nodes
  node_name    = each.key
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # A file on a node has one owner. pve-lab keeps the bare name this root created first (renaming it would
  # touch the disk source of the running first server); elsewhere the bare name belongs to another root
  # (deploy-runner on pve-core), so this root's copy is prefixed like the storage and postgresql ones.
  file_name          = each.key == "pve-lab" ? basename(var.image.url) : "k3s-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "node" {
  for_each            = var.nodes
  node_name           = each.value.node
  vm_id               = each.value.vm_id
  name                = each.key
  description         = "k3s ${each.value.role} (homelab-iac terraform/stacks/k3s, M004). Rebuildable: no data on this disk."
  tags                = ["terraform", "k3s", "k3s-${each.value.role}"]
  started             = true
  on_boot             = true
  reboot_after_update = false
  machine             = "q35"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  agent {
    enabled = true
    # The Debian generic cloud image has no guest agent until Ansible installs it: wait briefly, not 15 min.
    timeout = "2m"
  }
  cpu {
    cores = each.value.cores
    type  = "x86-64-v2-AES"
  }
  memory {
    dedicated = each.value.memory
  }
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    import_from  = proxmox_download_file.debian[each.value.node].id
    size         = each.value.disk_gb
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
    ignore_changes = [started]
  }
}
