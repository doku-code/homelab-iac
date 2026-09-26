mock_provider "proxmox" {}

variables {
  proxmox_endpoint = "https://proxmox.invalid:8006/"
  image            = { url = "https://example.invalid/debian-13-20260925.qcow2", sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
  servers = {
    server-1 = {
      node            = "mock-node", vm_id = 901, name = "lab-server-1"
      image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
      bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
    }
    server-2 = {
      node            = "mock-node", vm_id = 902, name = "lab-server-2"
      image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
      bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
    }
    server-3 = {
      node            = "mock-node", vm_id = 903, name = "lab-server-3"
      image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
      bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
    }
  }
}

run "headless" {
  command = plan
  assert {
    condition     = length(module.servers) == 3 && length(proxmox_download_file.linux) == 1
    error_message = "Exactly three VMs must share one image on the same node/datastore."
  }
  assert {
    condition = alltrue([for server in values(module.servers) : (
      length(server.vm.hostpci) == 0 && length(server.vm.usb) == 0 &&
      !contains(server.vm.tags, "workstation") &&
      !server.vm.started && !server.vm.on_boot && !server.vm.reboot_after_update &&
      server.vm.memory[0].dedicated == 4096 && server.vm.cpu[0].cores == 2 &&
      server.vm.disk[0].size == 32 && server.vm.disk[0].datastore_id == "mock-disks" &&
      server.vm.initialization[0].datastore_id == "mock-disks" &&
      server.vm.initialization[0].user_account[0].username == "debian"
    )])
    error_message = "Headless hardware, 4-GiB/local disk sizing or stopped lifecycle contract changed."
  }
  assert {
    condition     = output.ansible_inventory.all.children.k3s_lab.hosts["server-2"].ansible_host == "192.0.2.12" && output.ansible_inventory.all.children.k3s_lab.hosts["server-2"].stage_a_vm_id == 902
    error_message = "Inventory must derive from the same allocation, not separate defaults."
  }
}

run "duplicate_id" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-2 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-2"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-3 = {
        node            = "mock-node", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
    }
  }
  expect_failures = [var.servers]
}

run "duplicate_ip" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-2 = {
        node            = "mock-node", vm_id = 902, name = "lab-server-2"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-3 = {
        node            = "mock-node", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
    }
  }
  expect_failures = [var.servers]
}

run "duplicate_name" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-2 = {
        node            = "mock-node", vm_id = 902, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-3 = {
        node            = "mock-node", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
    }
  }
  expect_failures = [var.servers]
}

run "nonlocal_storage" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = false
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-2 = {
        node            = "mock-node", vm_id = 902, name = "lab-server-2"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = false
        bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-3 = {
        node            = "mock-node", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = false
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
    }
  }
  expect_failures = [var.servers]
}

run "undersized" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
        memory          = 2048
      }
      server-2 = {
        node            = "mock-node", vm_id = 902, name = "lab-server-2"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
        memory          = 2048
      }
      server-3 = {
        node            = "mock-node", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
        memory          = 2048
      }
    }
  }
  expect_failures = [var.servers]
}

run "missing_allocation" {
  command = plan
  variables { servers = {} }
  expect_failures = [var.servers]
}

run "missing_checksum" {
  command = plan
  variables { image = { url = "https://example.invalid/20260925.qcow2", sha256 = "" } }
  expect_failures = [var.image]
}

run "mutable_image" {
  command = plan
  variables { image = { url = "https://example.invalid/latest/20260925.qcow2", sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" } }
  expect_failures = [var.image]
}

run "alternate_placement" {
  command = plan
  variables {
    servers = {
      server-1 = {
        node            = "mock-node-1", vm_id = 901, name = "lab-server-1"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.11/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-2 = {
        node            = "mock-node-2", vm_id = 902, name = "lab-server-2"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.12/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
      server-3 = {
        node            = "mock-node-3", vm_id = 903, name = "lab-server-3"
        image_datastore = "mock-images", disk_datastore = "mock-disks", storage_local = true
        bridge          = "mock-bridge", ipv4 = "192.0.2.13/24", gateway = "192.0.2.1", dns_servers = ["192.0.2.53"]
      }
    }
  }
  assert {
    condition     = length(proxmox_download_file.linux) == 3 && module.servers["server-3"].vm.node_name == "mock-node-3"
    error_message = "Environment map must change placement without duplicated modules."
  }
}
