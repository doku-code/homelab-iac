mock_provider "proxmox" {}

variables {
  proxmox_endpoint = "https://proxmox.invalid:8006/"
  profile = {
    node            = "mock-node"
    vm_id           = 999
    name            = "synthetic-controller"
    image_datastore = "mock-images"
    disk_datastore  = "mock-disks"
    image_url       = "https://example.invalid/debian-13-20260925.qcow2"
    image_sha256    = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    bridge          = "mock-bridge"
    ipv4            = "192.0.2.10/24"
    gateway         = "192.0.2.1"
    dns_servers     = ["192.0.2.53"]
    cores           = 2
    memory          = 4096
    disk_gb         = 32
  }
}

run "headless" {
  command = plan
  assert {
    condition = (
      length(proxmox_virtual_environment_vm.controller.hostpci) == 0 &&
      length(proxmox_virtual_environment_vm.controller.usb) == 0 &&
      !contains(proxmox_virtual_environment_vm.controller.tags, "workstation") &&
      !proxmox_virtual_environment_vm.controller.started &&
      !proxmox_virtual_environment_vm.controller.reboot_after_update &&
      proxmox_virtual_environment_vm.controller.initialization[0].user_account[0].username == "debian"
    )
    error_message = "Headless VM must have no passthrough/workstation membership or automatic start."
  }
}

run "invalid_allocation" {
  command = plan
  variables {
    profile = {
      node      = "", vm_id = 0, name = "", image_datastore = "", disk_datastore = "",
      image_url = "https://example.invalid/latest/image", image_sha256 = "",
      bridge    = "", ipv4 = "dhcp", gateway = "", dns_servers = [], cores = 0, memory = 0, disk_gb = 0
    }
  }
  expect_failures = [var.profile]
}
