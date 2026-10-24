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
      length(vm.hostpci) == 0 && length(vm.usb) == 0 &&
      vm.vga[0].type == "std" && vm.vga[0].memory == 32 &&
      vm.tablet_device && vm.hook_script_file_id == ""
    ])
    error_message = "Preserve identity/disks/power policy and require virtual-only display/input."
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
    condition     = alltrue([for vm in proxmox_virtual_environment_vm.workstation : length(vm.hostpci) == 0 && length(vm.usb) == 0])
    error_message = "Legacy empty overrides must not reintroduce passthrough."
  }
}

run "invalid_mapping" {
  command = plan
  variables {
    hardware_profiles = { ubuntu = { gpu = false, usb_mappings = ["unknown"] } }
  }
  expect_failures = [var.hardware_profiles]
}

run "retired_gpu" {
  command = plan
  variables {
    hardware_profiles = { game = { gpu = true, usb_mappings = [] } }
  }
  expect_failures = [var.hardware_profiles]
}
