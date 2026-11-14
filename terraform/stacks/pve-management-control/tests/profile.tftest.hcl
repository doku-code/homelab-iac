# OpenTofu mocks generate computed values at plan time; give the image a valid volume ID
# so the provider's import_from validation sees a realistic identifier.
mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/mgmt-ubuntu-bbbbbbbbbbbbbbbb.qcow2"
    }
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile = {
    node            = "pve-management"
    vm_id           = 990
    name            = "mgmt-control-01"
    image_datastore = "mock-images"
    disk_datastore  = "mock-disks"
    bridge          = "mock-bridge"
    ipv4            = "192.0.2.50/24"
    gateway         = "192.0.2.1"
    dns_servers     = ["192.0.2.53"]
    cores           = 2
    memory          = 4096
    disk_gb         = 40
  }
  image = {
    url    = "https://cloud-images.ubuntu.com/releases/noble/release-20260101/ubuntu-24.04-server-cloudimg-amd64.img"
    sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }
}

run "management_vm_contract" {
  command = plan
  assert {
    condition = (
      module.control.vm.node_name == "pve-management" && module.control.vm.name == "mgmt-control-01" &&
      module.control.vm.vm_id == 990 && module.control.vm.started && module.control.vm.on_boot &&
      module.control.vm.cpu[0].cores == 2 && module.control.vm.memory[0].dedicated == 4096 &&
      module.control.vm.disk[0].size == 40 && module.control.vm.disk[0].datastore_id == "mock-disks" &&
      module.control.vm.disk[0].discard == "on" && module.control.vm.disk[0].ssd &&
      module.control.vm.cpu[0].type == "host" &&
      module.control.vm.network_device[0].bridge == "mock-bridge" &&
      length(module.control.vm.hostpci) == 0 && length(module.control.vm.usb) == 0
    )
    error_message = "Management VM placement, sizing or lifecycle contract changed."
  }
  assert {
    condition = (
      module.control.vm.initialization[0].user_account[0].username == "ubuntu" &&
      one(module.control.vm.initialization[0].user_account[0].keys) == trimspace(file("../../../keys/doku-lab-admin.pub")) &&
      module.control.vm.initialization[0].ip_config[0].ipv4[0].address == "192.0.2.50/24" &&
      contains(module.control.vm.tags, "management")
    )
    error_message = "Cloud-init user, key, static address or tags changed."
  }
  assert {
    condition = (
      proxmox_download_file.ubuntu.node_name == "pve-management" && proxmox_download_file.ubuntu.content_type == "import" &&
      proxmox_download_file.ubuntu.checksum == var.image.sha256 && proxmox_download_file.ubuntu.checksum_algorithm == "sha256" &&
      proxmox_download_file.ubuntu.datastore_id == "mock-images" && !proxmox_download_file.ubuntu.overwrite
    )
    error_message = "The image must be checksum-pinned, imported on pve-management and never overwritten."
  }
  assert {
    condition     = output.address == "192.0.2.50" && output.ansible_inventory.all.children.mgmt_control.hosts["mgmt-control-01"].ansible_user == "ubuntu"
    error_message = "Inventory must derive from the same allocation."
  }
}

run "rejects_other_nodes" {
  command = plan
  variables {
    profile = {
      node            = "pve-core"
      vm_id           = 990
      name            = "mgmt-control-01"
      image_datastore = "mock-images"
      disk_datastore  = "mock-disks"
      bridge          = "mock-bridge"
      ipv4            = "192.0.2.50/24"
      gateway         = "192.0.2.1"
      dns_servers     = ["192.0.2.53"]
      cores           = 2
      memory          = 4096
      disk_gb         = 40
    }
  }
  expect_failures = [var.profile]
}

run "rejects_dhcp" {
  command = plan
  variables {
    profile = {
      node            = "pve-management"
      vm_id           = 990
      name            = "mgmt-control-01"
      image_datastore = "mock-images"
      disk_datastore  = "mock-disks"
      bridge          = "mock-bridge"
      ipv4            = "dhcp"
      gateway         = "192.0.2.1"
      dns_servers     = ["192.0.2.53"]
      cores           = 2
      memory          = 4096
      disk_gb         = 40
    }
  }
  expect_failures = [var.profile]
}

run "rejects_unpinned_image" {
  command = plan
  variables {
    image = { url = "https://example.invalid/ubuntu.img", sha256 = "abc" }
  }
  expect_failures = [var.image]
}

run "rejects_plain_http_endpoint" {
  command = plan
  variables {
    proxmox_endpoint = "http://192.0.2.10:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}
