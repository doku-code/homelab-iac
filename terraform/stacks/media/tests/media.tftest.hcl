mock_provider "proxmox" {
  mock_resource "proxmox_download_file" {
    defaults = {
      id = "mock-images:import/media-debian-13-generic-amd64-20261123-2671.qcow2"
    }
  }
}

override_resource {
  target = proxmox_download_file.template
  values = {
    id = "local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  profile          = { node = "pve-infra", vm_id = 380, name = "media-01", ipv4 = "192.168.0.80/24", cores = 4, memory = 5632, os_disk_gb = 16, data_disk_gb = 140, gpu_mapping = "igpu" }
  image = {
    url    = "https://cloud.debian.org/images/cloud/trixie/20261123-2671/debian-13-generic-amd64-20261123-2671.qcow2"
    sha512 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  ssh_public_key = null
  containers = {
    jellyfin = { vm_id = 381, ipv4 = "192.168.0.81/24", cores = 4, memory = 3072, swap = 1024, disk_gb = 32 }
    seerr    = { vm_id = 382, ipv4 = "192.168.0.82/24", cores = 2, memory = 2048, swap = 3072, disk_gb = 12 }
    radarr   = { vm_id = 383, ipv4 = "192.168.0.83/24", cores = 2, memory = 1024, swap = 512, disk_gb = 8 }
    sonarr   = { vm_id = 384, ipv4 = "192.168.0.84/24", cores = 2, memory = 1024, swap = 512, disk_gb = 8 }
    prowlarr = { vm_id = 385, ipv4 = "192.168.0.85/24", cores = 1, memory = 768, swap = 512, disk_gb = 6 }
  }
  template = {
    url    = "http://download.proxmox.com/images/system/debian-13-standard_13.6-1_amd64.tar.zst"
    sha512 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }
}

run "one_container_per_service" {
  command = plan
  assert {
    condition = (
      length(proxmox_virtual_environment_container.service) == 5 &&
      alltrue([for c in proxmox_virtual_environment_container.service : c.node_name == "pve-infra" && c.unprivileged && c.start_on_boot && c.features[0].nesting]) &&
      proxmox_virtual_environment_container.service["jellyfin"].vm_id == 381 &&
      proxmox_virtual_environment_container.service["prowlarr"].initialization[0].ip_config[0].ipv4[0].address == "192.168.0.85/24" &&
      proxmox_virtual_environment_container.service["radarr"].initialization[0].hostname == "radarr" &&
      output.ansible_inventory.all.children.media.hosts["sonarr"].ansible_host == "192.168.0.84" &&
      output.ansible_inventory.all.children.media.hosts["sonarr"].media_service == "sonarr" &&
      length(output.ansible_inventory.all.children.media.hosts) == 5
    )
    error_message = "Five unprivileged containers on pve-infra, one per service, named after it, at .81 to .85."
  }
}

run "rejects_a_torrent_client_and_the_vm_address" {
  command = plan
  variables {
    containers = {
      qbittorrent = { vm_id = 386, ipv4 = "192.168.0.86/24", cores = 1, memory = 512, swap = 0, disk_gb = 6 }
      radarr      = { vm_id = 380, ipv4 = "192.168.0.80/24", cores = 1, memory = 512, swap = 0, disk_gb = 6 }
    }
  }
  expect_failures = [var.containers]
}

run "media_vm_contract" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_vm.media.node_name == "pve-infra" &&
      proxmox_virtual_environment_vm.media.vm_id == 380 &&
      !proxmox_virtual_environment_vm.media.on_boot &&
      length(proxmox_virtual_environment_vm.media.disk) == 2 &&
      proxmox_virtual_environment_vm.media.disk[1].interface == "scsi1" &&
      proxmox_virtual_environment_vm.media.hostpci[0].mapping == "igpu" &&
      proxmox_virtual_environment_vm.media.initialization[0].ip_config[0].ipv4[0].address == "192.168.0.80/24" &&
      proxmox_download_file.debian.file_name == "media-debian-13-generic-amd64-20261123-2671.qcow2"
    )
    error_message = "The retired media-01 stays VM 380 on pve-infra, as it was built, but no longer starts at boot."
  }
}

run "without_graphics_adapter" {
  command = plan
  variables {
    profile = { node = "pve-infra", vm_id = 380, name = "media-01", ipv4 = "192.168.0.80/24", cores = 4, memory = 5632, os_disk_gb = 16, data_disk_gb = 140, gpu_mapping = null }
  }
  assert {
    condition     = length(proxmox_virtual_environment_vm.media.hostpci) == 0
    error_message = "No mapping, no passed device."
  }
}

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}

run "rejects_other_ranges_and_a_raw_device" {
  command = plan
  variables {
    profile = { node = "pve-core", vm_id = 200, name = "media-01", ipv4 = "192.168.0.50/24", cores = 1, memory = 1024, os_disk_gb = 8, data_disk_gb = 10, gpu_mapping = "0000:00:02.0" }
  }
  expect_failures = [var.profile]
}
