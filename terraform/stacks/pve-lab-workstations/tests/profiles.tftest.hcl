mock_provider "proxmox" {}

variables {
  proxmox_endpoint = "https://proxmox.invalid:8006/"
}

run "existing_profiles" {
  command = plan
  assert {
    condition = alltrue([for k, vm in proxmox_virtual_environment_vm.workstation :
      vm.vm_id == local.workstation_vms[k].vm_id &&
      vm.network_device[0].mac_address == local.workstation_vms[k].mac_address &&
      vm.smbios[0].uuid == local.workstation_vms[k].smbios_uuid &&
      vm.disk[0].size == local.workstation_vms[k].disk_size &&
      !vm.started && !vm.on_boot && !vm.reboot_after_update &&
      length(vm.hostpci) == 1 && vm.hostpci[0].mapping == "pve-lab-workstation-gpu" &&
      [for u in vm.usb : u.mapping] == local.default_hardware.usb_mappings
    ])
    error_message = "Existing VM identity, disks, running policy or passthrough changed."
  }
  assert {
    condition     = toset(keys(proxmox_virtual_environment_vm.workstation)) == toset(["game", "dev", "school", "ubuntu", "fedora"])
    error_message = "Existing resource keys changed."
  }
}

run "optional_hardware" {
  command = plan
  variables {
    hardware_profiles = { ubuntu = { gpu = false, usb_mappings = [] } }
  }
  assert {
    condition     = length(proxmox_virtual_environment_vm.workstation["ubuntu"].hostpci) == 0 && length(proxmox_virtual_environment_vm.workstation["ubuntu"].usb) == 0 && length(proxmox_virtual_environment_vm.workstation["game"].hostpci) == 1
    error_message = "Hardware capabilities must be independently optional."
  }
}

run "invalid_mapping" {
  command = plan
  variables {
    hardware_profiles = { ubuntu = { gpu = false, usb_mappings = ["unknown"] } }
  }
  expect_failures = [var.hardware_profiles]
}
