mock_provider "proxmox" {}

variables {
  # Synthetic test fixtures, NOT approved allocations.
  routers = {
    ts-router-01 = {
      vm_id            = 99001
      ipv4_address     = "192.168.0.251/24"
      datastore_id     = "synthetic-local"
      template_file_id = "synthetic:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
    }
    ts-router-02 = {
      vm_id            = 99002
      ipv4_address     = "192.168.0.252/24"
      datastore_id     = "synthetic-local"
      template_file_id = "synthetic:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
    }
  }
}

run "independent_unprivileged_routers" {
  command = plan
  assert {
    condition = (
      length(proxmox_virtual_environment_container.router) == 2 &&
      proxmox_virtual_environment_container.router["ts-router-01"].node_name == "pve-k8s-01" &&
      proxmox_virtual_environment_container.router["ts-router-02"].node_name == "pve-k8s-02" &&
      alltrue([for r in proxmox_virtual_environment_container.router :
        r.unprivileged && r.started && r.start_on_boot && !r.features[0].nesting &&
        r.cpu[0].cores == 1 && r.memory[0].dedicated == 512 && r.disk[0].size == 8 &&
        r.device_passthrough[0].path == "/dev/net/tun" && r.device_passthrough[0].mode == "0666" &&
        length(r.network_interface) == 1
      ])
    )
    error_message = "Only two small independent unprivileged TUN-enabled routers are allowed."
  }
  assert {
    condition     = output.ansible_inventory.tailscale_routers.hosts["ts-router-02"].ansible_host == "192.168.0.252"
    error_message = "Inventory must derive from the same allocated resources."
  }
}

run "reject_duplicate_vmids" {
  command = plan
  variables {
    routers = { for name, r in var.routers : name => merge(r, { vm_id = 99001 }) }
  }
  expect_failures = [var.routers]
}

run "reject_duplicate_ips" {
  command = plan
  variables {
    routers = { for name, r in var.routers : name => merge(r, { ipv4_address = "192.168.0.251/24" }) }
  }
  expect_failures = [var.routers]
}

run "reject_unallocated_profile" {
  command = plan
  variables {
    routers = { for name, r in var.routers : name => merge(r, { vm_id = 0, ipv4_address = "TODO/24" }) }
  }
  expect_failures = [var.routers]
}
