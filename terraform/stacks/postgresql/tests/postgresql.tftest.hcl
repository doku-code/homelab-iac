mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/debian.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  nodes = {
    pg-01 = { node = "pve-core", vm_id = 361, ipv4 = "192.168.0.61/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40, failover_priority = 2 }
    pg-02 = { node = "pve-lab", vm_id = 362, ipv4 = "192.168.0.62/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40, failover_priority = 2 }
    pg-03 = { node = "pve-infra", vm_id = 363, ipv4 = "192.168.0.63/24", cores = 2, memory = 2048, os_disk_gb = 16, data_disk_gb = 40 }
  }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
}

run "three_members_on_three_hosts" {
  command = plan
  assert {
    condition = (
      length(proxmox_virtual_environment_vm.node) == 3 && length(proxmox_download_file.debian) == 3 &&
      proxmox_virtual_environment_vm.node["pg-03"].node_name == "pve-infra" &&
      proxmox_virtual_environment_vm.node["pg-01"].vm_id == 361 &&
      length(proxmox_virtual_environment_vm.node["pg-01"].disk) == 2 &&
      proxmox_virtual_environment_vm.node["pg-01"].disk[1].interface == "scsi1" &&
      proxmox_virtual_environment_vm.node["pg-01"].disk[1].size == 40 &&
      proxmox_download_file.debian["pve-lab"].file_name == "postgresql-debian-13-genericcloud-amd64-20261116-2664.qcow2"
    )
    error_message = "Three members, one per Proxmox host, each with a separate data disk and its own image copy."
  }
  assert {
    condition = (
      output.virtual_ip == "192.168.0.60" && output.addresses["pg-02"] == "192.168.0.62" &&
      output.ansible_inventory.all.children.postgresql.vars.patroni_virtual_ip == "192.168.0.60" &&
      output.ansible_inventory.all.children.postgresql.hosts["pg-03"].patroni_failover_priority == 1 &&
      output.ansible_inventory.all.children.postgresql.hosts["pg-01"].patroni_failover_priority == 2
    )
    error_message = "The inventory carries the virtual IP and each member's failover priority (default 1)."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_two_members_on_one_host" {
  command = plan
  variables {
    nodes = {
      pg-01 = { node = "pve-core", vm_id = 361, ipv4 = "192.168.0.61/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40 }
      pg-02 = { node = "pve-core", vm_id = 362, ipv4 = "192.168.0.62/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40 }
      pg-03 = { node = "pve-infra", vm_id = 363, ipv4 = "192.168.0.63/24", cores = 2, memory = 2048, os_disk_gb = 16, data_disk_gb = 40 }
    }
  }
  expect_failures = [var.nodes]
}

run "rejects_foreign_ranges_and_the_virtual_ip" {
  command = plan
  variables {
    nodes = {
      pg-01 = { node = "pve-core", vm_id = 361, ipv4 = "192.168.0.60/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40 }
      pg-02 = { node = "pve-lab", vm_id = 310, ipv4 = "192.168.0.40/24", cores = 2, memory = 4096, os_disk_gb = 16, data_disk_gb = 40 }
      pg-03 = { node = "pve-management", vm_id = 363, ipv4 = "192.168.0.63/24", cores = 2, memory = 2048, os_disk_gb = 16, data_disk_gb = 400 }
    }
  }
  expect_failures = [var.nodes]
}
