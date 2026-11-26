mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/media-debian-13-generic-amd64-20261123-2671.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile          = { node = "pve-infra", vm_id = 380, name = "media-01", ipv4 = "192.168.0.80/24", cores = 4, memory = 5632, os_disk_gb = 16, data_disk_gb = 140, gpu_mapping = "igpu" }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261123-2671/debian-13-generic-amd64-20261123-2671.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
}

run "media_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.media.node_name == "pve-infra" &&
      proxmox_virtual_environment_vm.media.vm_id == 380 &&
      proxmox_virtual_environment_vm.media.on_boot &&
      length(proxmox_virtual_environment_vm.media.disk) == 2 &&
      proxmox_virtual_environment_vm.media.disk[1].interface == "scsi1" &&
      proxmox_virtual_environment_vm.media.hostpci[0].mapping == "igpu" &&
      proxmox_virtual_environment_vm.media.initialization[0].ip_config[0].ipv4[0].address == "192.168.0.80/24" &&
      proxmox_download_file.debian.file_name == "media-debian-13-generic-amd64-20261123-2671.qcow2" &&
      output.ansible_inventory.all.children.media.hosts["media-01"].ansible_host == "192.168.0.80" &&
      output.ansible_inventory.all.children.media.hosts["media-01"].media_gpu
    )
    error_message = "media-01 is VM 380 on pve-infra at .80 with a data disk, its own image copy and the mapped graphics adapter."
  }
}

run "without_graphics_adapter" {
  command = plan
  variables {
    profile = { node = "pve-infra", vm_id = 380, name = "media-01", ipv4 = "192.168.0.80/24", cores = 4, memory = 5632, os_disk_gb = 16, data_disk_gb = 140, gpu_mapping = null }
  }
  assert {
    condition     = length(proxmox_virtual_environment_vm.media.hostpci) == 0 && !output.ansible_inventory.all.children.media.hosts["media-01"].media_gpu
    error_message = "No mapping, no passed device."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_other_ranges_and_a_raw_device" {
  command = plan
  variables {
    profile = { node = "pve-core", vm_id = 200, name = "media-01", ipv4 = "192.168.0.50/24", cores = 1, memory = 1024, os_disk_gb = 8, data_disk_gb = 10, gpu_mapping = "0000:00:02.0" }
  }
  expect_failures = [var.profile]
}
