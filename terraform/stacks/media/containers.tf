# The media services, one unprivileged container each on pve-infra (TASK-036, operator's choice of 2026-11-26:
# separate guests in the Proxmox tree instead of one Compose VM). What only root@pam may set (the mounts of the
# host's directories and the graphics device of Jellyfin) is added by scripts/pve-media-mounts.sh
# (`make media-mounts`), which is why those two blocks are ignored here.
resource "proxmox_download_file" "template" {
  node_name          = var.node
  datastore_id       = var.image_datastore
  content_type       = "vztmpl"
  url                = var.template.url
  checksum           = var.template.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_container" "service" {
  for_each = var.containers

  node_name     = var.node
  vm_id         = each.value.vm_id
  description   = "${each.key}: media stack (homelab-iac terraform/stacks/media, TASK-036). Rebuildable from Git; its application data is on its own disk."
  tags          = ["terraform", "media"]
  unprivileged  = true
  started       = true
  start_on_boot = true

  # systemd in an unprivileged Debian 13 container needs nesting.
  features {
    nesting = true
  }
  cpu {
    cores = each.value.cores
  }
  memory {
    dedicated = each.value.memory
    swap      = each.value.swap
  }
  disk {
    datastore_id = var.disk_datastore
    size         = each.value.disk_gb
  }
  network_interface {
    name     = "eth0"
    bridge   = var.bridge
    firewall = true
  }
  initialization {
    hostname = each.key
    dns {
      servers = var.dns_servers
    }
    ip_config {
      ipv4 {
        address = each.value.ipv4
        gateway = var.gateway
      }
    }
    user_account {
      keys = [trimspace(coalesce(var.ssh_public_key, file("${path.module}/../../../keys/mgmt-control-01.pub")))]
    }
  }
  operating_system {
    template_file_id = proxmox_download_file.template.id
    type             = "debian"
  }
  lifecycle {
    # The template is only read at creation; mounts and devices belong to `make media-mounts`.
    ignore_changes = [started, operating_system[0].template_file_id, mount_point, device_passthrough]
  }
}
