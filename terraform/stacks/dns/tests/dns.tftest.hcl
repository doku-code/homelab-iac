mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/dns-debian-13-genericcloud-amd64-20261116-2664.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile          = { node = "pve-infra", vm_id = 370, name = "dns-01", ipv4 = "192.168.0.70/24", cores = 1, memory = 1024, os_disk_gb = 10 }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
}

run "dns_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.dns.node_name == "pve-infra" &&
      proxmox_virtual_environment_vm.dns.vm_id == 370 &&
      proxmox_virtual_environment_vm.dns.on_boot &&
      length(proxmox_virtual_environment_vm.dns.disk) == 1 &&
      proxmox_virtual_environment_vm.dns.initialization[0].ip_config[0].ipv4[0].address == "192.168.0.70/24" &&
      proxmox_virtual_environment_vm.dns.initialization[0].dns[0].servers[0] == "9.9.9.9" &&
      proxmox_download_file.debian.file_name == "dns-debian-13-genericcloud-amd64-20261116-2664.qcow2" &&
      output.ansible_inventory.all.children.dns.hosts["dns-01"].ansible_host == "192.168.0.70"
    )
    error_message = "dns-01 is VM 370 on pve-infra at .70 with its own image copy and public resolvers for itself."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_the_service_address_and_other_ranges" {
  command = plan
  variables {
    profile = { node = "pve-management", vm_id = 200, name = "dns-01", ipv4 = "192.168.0.20/24", cores = 1, memory = 512, os_disk_gb = 8 }
  }
  expect_failures = [var.profile]
}
