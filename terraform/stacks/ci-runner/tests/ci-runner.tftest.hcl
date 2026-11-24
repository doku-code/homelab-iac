mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/ci-runner-debian-13-genericcloud-amd64-20261116-2664.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile          = { node = "pve-core", vm_id = 303, name = "ci-runner-01", ipv4 = "192.168.0.33/24", cores = 4, memory = 6144, os_disk_gb = 48 }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
}

run "runner_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.runner.node_name == "pve-core" &&
      proxmox_virtual_environment_vm.runner.vm_id == 303 &&
      proxmox_virtual_environment_vm.runner.name == "ci-runner-01" &&
      proxmox_virtual_environment_vm.runner.on_boot &&
      proxmox_virtual_environment_vm.runner.disk[0].size == 48 &&
      proxmox_virtual_environment_vm.runner.initialization[0].ip_config[0].ipv4[0].address == "192.168.0.33/24" &&
      proxmox_virtual_environment_vm.runner.initialization[0].dns[0].servers[0] == "192.168.0.20" &&
      proxmox_download_file.debian.file_name == "ci-runner-debian-13-genericcloud-amd64-20261116-2664.qcow2" &&
      output.ansible_inventory.all.children.ci_runner.hosts["ci-runner-01"].ansible_host == "192.168.0.33"
    )
    error_message = "ci-runner-01 is VM 303 on pve-core at .33 with its own image copy and the LAN resolver."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_the_deployment_runner_allocation_and_small_sizes" {
  command = plan
  variables {
    profile = { node = "pve-core", vm_id = 302, name = "ci-runner-01", ipv4 = "192.168.0.32/24", cores = 1, memory = 2048, os_disk_gb = 16 }
  }
  expect_failures = [var.profile]
}
