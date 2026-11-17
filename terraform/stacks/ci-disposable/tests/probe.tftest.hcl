mock_provider "proxmox" {}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
}

run "probe_is_disposable" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.probe.vm_id == 9900 && proxmox_virtual_environment_vm.probe.pool_id == "ci-disposable" &&
      !proxmox_virtual_environment_vm.probe.started && !proxmox_virtual_environment_vm.probe.on_boot &&
      proxmox_virtual_environment_vm.probe.disk[0].size == 1 && length(proxmox_virtual_environment_vm.probe.network_device) == 0 &&
      proxmox_virtual_environment_vm.probe.memory[0].dedicated == 128
    )
    error_message = "The probe must stay a stopped, tiny, NIC-less VM in the ci-disposable pool."
  }
}

run "rejects_vmid_outside_ci_range" {
  command = plan
  variables {
    vm_id = 302
  }
  expect_failures = [var.vm_id]
}

run "rejects_other_pool" {
  command = plan
  variables {
    pool = "production"
  }
  expect_failures = [var.pool]
}
