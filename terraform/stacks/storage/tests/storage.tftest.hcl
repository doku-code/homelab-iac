mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/debian.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile          = { node = "pve-core", vm_id = 350, name = "storage-01", ipv4 = "192.168.0.50/24", cores = 2, memory = 2048, os_disk_gb = 16, data_disk_gb = 300 }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
}

run "storage_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.storage.node_name == "pve-core" && proxmox_virtual_environment_vm.storage.vm_id == 350 &&
      proxmox_virtual_environment_vm.storage.started && proxmox_virtual_environment_vm.storage.on_boot &&
      length(proxmox_virtual_environment_vm.storage.disk) == 2 &&
      proxmox_virtual_environment_vm.storage.disk[0].interface == "scsi0" && proxmox_virtual_environment_vm.storage.disk[0].size == 16 &&
      proxmox_virtual_environment_vm.storage.disk[1].interface == "scsi1" && proxmox_virtual_environment_vm.storage.disk[1].size == 300 &&
      proxmox_virtual_environment_vm.storage.disk[1].discard == "on" &&
      output.address == "192.168.0.50"
    )
    error_message = "storage-01 is VM 350 on pve-core with a 16 GiB OS disk and a separate 300 GiB data disk."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_other_nodes_ranges_and_oversized_disks" {
  command = plan
  variables {
    profile = { node = "pve-lab", vm_id = 310, name = "x", ipv4 = "192.168.0.40/24", cores = 2, memory = 2048, os_disk_gb = 16, data_disk_gb = 900 }
  }
  expect_failures = [var.profile]
}
