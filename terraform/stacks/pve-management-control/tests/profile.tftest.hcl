# OpenTofu mocks generate computed values at plan time; give the ISO a valid volume ID.
mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:iso/ubuntu-26.04.1-desktop-amd64.iso"
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
  desktop_iso = {
    url    = "https://releases.ubuntu.com/26.04.1/ubuntu-26.04.1-desktop-amd64.iso"
    sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }
  autoinstall_seed_url = "http://192.0.2.9:8399/"
  workstation_enabled  = true # explicit: a local terraform.tfvars must not change the tests
}

run "management_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.workstation[0].node_name == "pve-management" &&
      proxmox_virtual_environment_vm.workstation[0].name == "mgmt-control-01" &&
      proxmox_virtual_environment_vm.workstation[0].vm_id == 990 &&
      proxmox_virtual_environment_vm.workstation[0].started && proxmox_virtual_environment_vm.workstation[0].on_boot &&
      proxmox_virtual_environment_vm.workstation[0].cpu[0].cores == 2 && proxmox_virtual_environment_vm.workstation[0].cpu[0].type == "host" &&
      proxmox_virtual_environment_vm.workstation[0].memory[0].dedicated == 4096 &&
      proxmox_virtual_environment_vm.workstation[0].disk[0].size == 40 &&
      proxmox_virtual_environment_vm.workstation[0].disk[0].datastore_id == "mock-disks" &&
      proxmox_virtual_environment_vm.workstation[0].disk[0].discard == "on" && proxmox_virtual_environment_vm.workstation[0].disk[0].ssd &&
      proxmox_virtual_environment_vm.workstation[0].network_device[0].bridge == "mock-bridge" &&
      length(proxmox_virtual_environment_vm.workstation[0].hostpci) == 0 && length(proxmox_virtual_environment_vm.workstation[0].usb) == 0 &&
      output.ansible_inventory.all.children.mgmt_control.hosts["mgmt-control-01"].gpu_passthrough == false
    )
    error_message = "Management VM placement, sizing or lifecycle contract changed."
  }
  assert {
    condition = (
      proxmox_virtual_environment_vm.workstation[0].cdrom[0].file_id == "mock-images:iso/ubuntu-26.04.1-desktop-amd64.iso" &&
      proxmox_virtual_environment_vm.workstation[0].boot_order == tolist(["scsi0", "ide2"]) &&
      proxmox_virtual_environment_vm.workstation[0].vga[0].type == "std" &&
      proxmox_virtual_environment_vm.workstation[0].smbios[0].serial == "ds=nocloud;s=http://192.0.2.9:8399/" &&
      length(proxmox_virtual_environment_vm.workstation[0].initialization) == 0
    )
    error_message = "The VM must boot the Desktop ISO, show a console display and find the autoinstall seed."
  }
  assert {
    condition = (
      proxmox_download_file.desktop_iso.content_type == "iso" && proxmox_download_file.desktop_iso.checksum == var.desktop_iso.sha256 &&
      proxmox_download_file.desktop_iso.checksum_algorithm == "sha256" && !proxmox_download_file.desktop_iso.overwrite &&
      proxmox_download_file.desktop_iso.file_name == "ubuntu-26.04.1-desktop-amd64.iso"
    )
    error_message = "The ISO must be checksum-pinned and never overwritten."
  }
  assert {
    condition = (
      startswith(output.autoinstall_user_data, "#cloud-config\n") &&
      strcontains(output.autoinstall_user_data, "hostname: mgmt-control-01") &&
      strcontains(output.autoinstall_user_data, "addresses: [192.0.2.50/24]") &&
      strcontains(output.autoinstall_user_data, trimspace(file("../../../keys/doku-lab-admin.pub"))) &&
      strcontains(output.autoinstall_user_data, "password: \"@MGMT_PASSWORD_HASH@\"") &&
      strcontains(output.autoinstall_user_data, "/target/home/ubuntu/.ssh/authorized_keys") &&
      strcontains(output.autoinstall_user_data, "PasswordAuthentication no") &&
      !strcontains(output.autoinstall_user_data, "passwd -l") &&
      strcontains(output.autoinstall_user_data, "allow-pw: false")
    )
    error_message = "Autoinstall must carry the allocation, the operator key, key-only SSH written without cloud-init and a password placeholder."
  }
  assert {
    condition     = output.address == "192.0.2.50" && output.ansible_inventory.all.children.mgmt_control.hosts["mgmt-control-01"].ansible_user == "ubuntu"
    error_message = "Inventory must derive from the same allocation."
  }
}

run "reinstall_first_step_creates_no_vm" {
  command = plan
  variables {
    workstation_enabled = false
  }
  assert {
    condition     = length(proxmox_virtual_environment_vm.workstation) == 0
    error_message = "With workstation_enabled = false the plan must not create the VM."
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

run "rejects_unofficial_iso" {
  command = plan
  variables {
    desktop_iso = { url = "https://example.invalid/ubuntu-desktop-amd64.iso", sha256 = "abc" }
  }
  expect_failures = [var.desktop_iso]
}

run "rejects_plain_http_endpoint" {
  command = plan
  variables {
    proxmox_endpoint = "http://192.0.2.10:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "graphics_adapter_passed_through_a_mapping" {
  command = plan
  variables {
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
      gpu_mapping     = "mock-gpu"
    }
  }
  assert {
    condition = (
      length(proxmox_virtual_environment_vm.workstation[0].hostpci) == 1 &&
      proxmox_virtual_environment_vm.workstation[0].hostpci[0].mapping == "mock-gpu" &&
      proxmox_virtual_environment_vm.workstation[0].hostpci[0].id == null &&
      !proxmox_virtual_environment_vm.workstation[0].hostpci[0].xvga &&
      proxmox_virtual_environment_vm.workstation[0].vga[0].type == "std" &&
      proxmox_virtual_environment_vm.workstation[0].protection &&
      output.ansible_inventory.all.children.mgmt_control.hosts["mgmt-control-01"].gpu_passthrough
    )
    error_message = "The graphics adapter must come from a resource mapping, beside the console display, on a protected VM."
  }
}
