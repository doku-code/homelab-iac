resource "proxmox_virtual_environment_vm" "workstation" {
  for_each = local.workstation_vms

  node_name = local.workstation_node
  vm_id     = each.value.vm_id
  name      = each.value.name

  tags = concat(
    local.workstation_profile.tags,
    each.value.tags
  )

  started = false
  on_boot = false

  # Terraform ne doit jamais décider tout seul
  # de reboot/shutdown une workstation active.
  reboot_after_update = false

  agent {
    enabled = each.value.agent_enabled
  }

  bios    = "ovmf"
  machine = each.value.machine

  boot_order = each.value.boot_order

  cpu {
    sockets = local.workstation_profile.sockets
    cores   = local.workstation_profile.cores
    type    = local.workstation_profile.cpu_type
    numa    = false
  }

  memory {
    dedicated = local.workstation_profile.memory
    floating  = local.workstation_profile.balloon
  }

  # GPU Passthrough section
  hostpci {
    device  = "hostpci0"
    mapping = "pve-lab-workstation-gpu"
    pcie    = true
    rombar  = true
    xvga    = true
  }

  # KVM section
  usb {
    mapping = "pve-lab-workstation-logitech"
    usb3    = true
  }

  usb {
    mapping = "pve-lab-workstation-keyboard"
    usb3    = true
  }

  usb {
    mapping = "pve-lab-workstation-brio"
    usb3    = true
  }

  usb {
    mapping = "pve-lab-workstation-scarlett"
    usb3    = true
  }

  efi_disk {
    datastore_id      = local.workstation_datastore
    type              = "4m"
    pre_enrolled_keys = true
  }

  dynamic "tpm_state" {
    for_each = each.value.tpm ? [1] : []

    content {
      datastore_id = local.workstation_datastore
      version      = "v2.0"
    }
  }

  disk {
    datastore_id = local.workstation_datastore
    interface    = "scsi0"

    size     = each.value.disk_size
    discard  = each.value.disk_discard
    iothread = true
    ssd      = each.value.disk_ssd
  }

  scsi_hardware = "virtio-scsi-single"

  dynamic "cdrom" {
    for_each = each.value.cdrom ? [1] : []

    content {
      interface = "ide2"
      file_id   = "none"
    }
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    firewall    = true
    mac_address = each.value.mac_address

    # Corrige volontairement le link_down accidentel de 502.
    disconnected = false
  }

  operating_system {
    type = each.value.os_type
  }

  smbios {
    uuid = each.value.smbios_uuid
  }

  lifecycle {
    prevent_destroy = true

    ignore_changes = [
      started,
      cpu[0].affinity,
      hook_script_file_id,
    ]
  }
}
