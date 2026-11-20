# API-token authentication only (PROXMOX_VE_API_TOKEN, checked by scripts/pve-auth-guard.py).
# No SSH block: ISO downloads and VM creation use the API (bpg/proxmox v0.112.0).
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

# Official Ubuntu Desktop ISO, verified against the release SHA256SUMS by Proxmox itself.
resource "proxmox_download_file" "desktop_iso" {
  node_name          = var.profile.node
  datastore_id       = var.profile.image_datastore
  content_type       = "iso"
  url                = var.desktop_iso.url
  file_name          = basename(var.desktop_iso.url)
  checksum           = var.desktop_iso.sha256
  checksum_algorithm = "sha256"
  overwrite          = false
  upload_timeout     = 3600
}

# mgmt-control-01: a regular Ubuntu Desktop (GNOME) installed from the official ISO by autoinstall
# (ADR-009). The installer reads its configuration over HTTP from the operator workstation
# (`make mgmt-autoinstall-serve`), located through the SMBIOS serial (cloud-init NoCloud), and asks
# for one confirmation on the Proxmox console before it erases the disk.
resource "proxmox_virtual_environment_vm" "workstation" {
  count = var.workstation_enabled ? 1 : 0

  node_name           = var.profile.node
  vm_id               = var.profile.vm_id
  name                = var.profile.name
  description         = "Operator workstation (Ubuntu Desktop). Managed by homelab-iac terraform/stacks/pve-management-control."
  tags                = ["terraform", "management", "mgmt-control"]
  started             = true
  on_boot             = true
  reboot_after_update = false
  protection          = true # Proxmox refuses to remove this VM or its disk
  machine             = "q35"
  bios                = "seabios"
  scsi_hardware       = "virtio-scsi-single"
  # Empty disk first: the ISO boots until the installer has written the disk, then the disk boots.
  boot_order = ["scsi0", "ide2"]

  agent {
    enabled = true
    timeout = "2m" # no agent in the live installer; the installed system runs it
  }
  cpu {
    cores = var.profile.cores
    type  = "host" # standalone host, no live migration: AVX2 for software rendering (GNOME, RDP, Zed)
  }
  memory {
    dedicated = var.profile.memory
  }
  vga {
    type   = "std" # the Proxmox console shows the GDM login screen and the desktop
    memory = 32
  }
  # The host's graphics adapter, through a Proxmox resource mapping (`make mgmt-gpu-mapping`): GNOME, the
  # editors and the browsers then render on it instead of on the CPU. The virtual display above stays for
  # the Proxmox console. Proxmox takes the device from the host's driver when the VM starts.
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
  disk {
    datastore_id = var.profile.disk_datastore
    interface    = "scsi0"
    file_format  = "raw"
    size         = var.profile.disk_gb
    discard      = "on" # return deleted guest blocks to the local-lvm thin pool
    ssd          = true
  }
  cdrom {
    interface = "ide2"
    file_id   = proxmox_download_file.desktop_iso.id
  }
  smbios {
    serial = "ds=nocloud;s=${var.autoinstall_seed_url}"
  }
  network_device {
    bridge   = var.profile.bridge
    model    = "virtio"
    firewall = true
  }
  operating_system {
    type = "l26"
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [started]
  }
}

# The former server cloud image stays on `local` (deleting files needs Datastore.Allocate, which the
# token deliberately lacks); OpenTofu stops tracking it. Delete it from the Proxmox UI when convenient.
removed {
  from = proxmox_download_file.ubuntu
  lifecycle {
    destroy = false
  }
}
