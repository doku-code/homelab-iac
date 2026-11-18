mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  nodes = {
    "k3s-server-01" = { node = "pve-lab", vm_id = 310, role = "server", ipv4 = "192.168.0.40/24", cores = 6, memory = 12288, disk_gb = 64 }
  }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null # explicit: a local terraform.tfvars must not change the tests
}

run "first_server_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.node["k3s-server-01"].node_name == "pve-lab" &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].vm_id == 310 &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].started &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].on_boot &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].cpu[0].cores == 6 &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].memory[0].dedicated == 12288 &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].disk[0].size == 64 &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].disk[0].import_from == "mock-images:import/debian-13-genericcloud-amd64-20261116-2664.qcow2" &&
      proxmox_virtual_environment_vm.node["k3s-server-01"].initialization[0].ip_config[0].ipv4[0].address == "192.168.0.40/24" &&
      startswith(proxmox_virtual_environment_vm.node["k3s-server-01"].initialization[0].user_account[0].keys[0], "ssh-ed25519 ") &&
      contains(proxmox_virtual_environment_vm.node["k3s-server-01"].tags, "k3s-server") &&
      length(proxmox_download_file.debian) == 1
    )
    error_message = "The first k3s server must be VM 310 on pve-lab, 6 vCPU / 12 GiB / 64 GiB, .40, workstation key."
  }
  assert {
    condition     = output.api_endpoint == "https://192.168.0.40:6443" && output.ansible_inventory.all.children.k3s_cluster.vars.k3s_init_node == "k3s-server-01"
    error_message = "The API endpoint and the cluster-init node come from the first server."
  }
}

run "one_image_per_proxmox_node" {
  command = plan
  variables {
    nodes = {
      "k3s-server-01" = { node = "pve-lab", vm_id = 310, role = "server", ipv4 = "192.168.0.40/24", cores = 6, memory = 12288, disk_gb = 64 }
      "k3s-server-02" = { node = "pve-core", vm_id = 311, role = "server", ipv4 = "192.168.0.41/24", cores = 4, memory = 8192, disk_gb = 64 }
      "k3s-agent-01"  = { node = "pve-lab", vm_id = 320, role = "agent", ipv4 = "192.168.0.42/24", cores = 2, memory = 4096, disk_gb = 32 }
    }
  }
  assert {
    condition     = length(proxmox_download_file.debian) == 2 && output.ansible_inventory.all.children.k3s_cluster.vars.k3s_init_node == "k3s-server-01"
    error_message = "Each hosting Proxmox node gets one image; the first server by name initialises etcd."
  }
  assert {
    condition = (
      proxmox_download_file.debian["pve-lab"].file_name == "debian-13-genericcloud-amd64-20261116-2664.qcow2" &&
      proxmox_download_file.debian["pve-core"].file_name == "k3s-debian-13-genericcloud-amd64-20261116-2664.qcow2"
    )
    error_message = "pve-lab keeps the image name of the running first server; other nodes get this root's own prefixed copy."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_workstation_node_dhcp_range_and_ci_vmids" {
  command = plan
  variables {
    nodes = {
      "bad" = { node = "pve-management", vm_id = 9901, role = "server", ipv4 = "192.168.0.150/24", cores = 1, memory = 1024, disk_gb = 8 }
    }
  }
  expect_failures = [var.nodes]
}

run "requires_a_server" {
  command = plan
  variables {
    nodes = {
      "k3s-agent-01" = { node = "pve-lab", vm_id = 320, role = "agent", ipv4 = "192.168.0.42/24", cores = 2, memory = 4096, disk_gb = 32 }
    }
  }
  expect_failures = [var.nodes]
}
