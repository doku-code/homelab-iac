# Media VM (TASK-036): Jellyfin, Seerr, Radarr, Sonarr, Prowlarr and qBittorrent under Docker Compose, outside
# k3s by the operator's choice (a test of the whole chain beside Plex, which keeps running on the NAS).
# Two disks: the system, and a data disk for the applications' configuration, Jellyfin's metadata and cache and
# the test area (downloads and what Radarr and Sonarr import). The NAS library is mounted read-only by Docker,
# for Jellyfin only (ansible/roles/media_stack). A test: no prevent_destroy; the databases live on the shared
# PostgreSQL and the configuration is archived every night (see docs/guides/media-stack.md).
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_download_file" "debian" {
  node_name    = var.profile.node
  datastore_id = var.image_datastore
  content_type = "import"
  url          = var.image.url
  # Own copy: a file on a node has one owner (another root may hold the same image on this node).
  file_name          = "media-${basename(var.image.url)}"
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

resource "proxmox_virtual_environment_vm" "media" {
  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  description         = "RETIRED on 2026-11-27: replaced by one container per service (containers.tf). Stopped, kept until the operator approves its deletion (homelab-iac terraform/stacks/media, TASK-036)."
  tags                = ["terraform", "media"]
  started             = true
  on_boot             = false
  reboot_after_update = false
  machine             = "q35"
  bios                = "seabios"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  agent {
    enabled = true
    timeout = "2m"
  }
  cpu {
    cores = var.profile.cores
    # The host's own processor: the VM cannot move anyway once it holds the graphics adapter, and software
    # transcoding (the fallback) uses every instruction the processor has.
    type = "host"
  }
  memory {
    dedicated = var.profile.memory
  }
  # The host's graphics adapter for hardware transcoding in Jellyfin, through a Proxmox resource mapping
  # (`make media-gpu-mapping`). Proxmox takes the device from the host's driver when the VM starts: the
  # host's own screen goes dark, its web interface and SSH are unaffected. The virtual display stays for the
  # Proxmox console. Same settings as the workstation VM (terraform/stacks/pve-management-control).
  dynamic "hostpci" {
    for_each = var.profile.gpu_mapping == null ? [] : [var.profile.gpu_mapping]
    content {
      device  = "hostpci0"
      mapping = hostpci.value
      pcie    = false
      rombar  = true
      xvga    = false
    }
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
    # The image is only read when the VM is created.
    ignore_changes = [started, disk[0].import_from]
  }
}
