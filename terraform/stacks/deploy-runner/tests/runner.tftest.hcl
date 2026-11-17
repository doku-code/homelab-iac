mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile = {
    node            = "pve-core"
    vm_id           = 302
    name            = "deploy-runner-01"
    image_datastore = "mock-images"
    disk_datastore  = "mock-disks"
    bridge          = "mock-bridge"
    ipv4            = "192.0.2.32/24"
    gateway         = "192.0.2.1"
    dns_servers     = ["192.0.2.53"]
    cores           = 6
    memory          = 8192
    disk_gb         = 24
  }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261116-2664/debian-13-genericcloud-amd64-20261116-2664.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null # explicit: a local terraform.tfvars must not change the tests
}

run "runner_vm_contract" {
  command = plan
  assert {
    condition = (
      module.runner.vm.node_name == "pve-core" && module.runner.vm.vm_id == 302 &&
      module.runner.vm.name == "deploy-runner-01" &&
      module.runner.vm.started && module.runner.vm.on_boot &&
      module.runner.vm.cpu[0].cores == 6 && module.runner.vm.memory[0].dedicated == 8192 &&
      module.runner.vm.disk[0].size == 24 && module.runner.vm.disk[0].datastore_id == "mock-disks" &&
      module.runner.vm.disk[0].discard == "on" && module.runner.vm.disk[0].ssd &&
      module.runner.vm.disk[0].import_from == "mock-images:import/debian-13-genericcloud-amd64-20261116-2664.qcow2" &&
      module.runner.vm.network_device[0].bridge == "mock-bridge" &&
      contains(module.runner.vm.tags, "deploy-runner")
    )
    error_message = "Runner placement, sizing, image or lifecycle contract changed."
  }
  assert {
    condition = (
      module.runner.vm.initialization[0].ip_config[0].ipv4[0].address == "192.0.2.32/24" &&
      module.runner.vm.initialization[0].user_account[0].username == "debian" &&
      module.runner.vm.initialization[0].user_account[0].keys == tolist([trimspace(file("../../../keys/mgmt-control-01.pub"))])
    )
    error_message = "Cloud-init must set the static address and only the workstation key for the debian user."
  }
  assert {
    condition = (
      proxmox_download_file.debian.content_type == "import" && proxmox_download_file.debian.checksum_algorithm == "sha512" &&
      proxmox_download_file.debian.checksum == var.image.sha512 && !proxmox_download_file.debian.overwrite
    )
    error_message = "The image must be checksum-pinned (SHA512) and never overwritten."
  }
  assert {
    condition = (
      output.address == "192.0.2.32" &&
      output.ansible_inventory.all.children.deploy_runner.hosts["deploy-runner-01"].ansible_user == "debian"
    )
    error_message = "Inventory output must follow the allocation."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_other_nodes_and_ci_vmids" {
  command = plan
  variables {
    profile = {
      node = "pve-lab", vm_id = 9901, name = "x", image_datastore = "a", disk_datastore = "b", bridge = "c"
      ipv4 = "192.0.2.32/24", gateway = "192.0.2.1", dns_servers = [], cores = 2, memory = 2048, disk_gb = 24
    }
  }
  expect_failures = [var.profile]
}
