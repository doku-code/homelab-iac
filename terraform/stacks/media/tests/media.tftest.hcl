mock_provider "proxmox" {}

override_resource {
  target = proxmox_download_file.template
  values = {
    id = "local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst"
  }
}

variables {
  proxmox_endpoint = "https://pve-management.invalid:8006/"
  ssh_public_key   = null
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
  assert {
    condition     = length([for r in [for name in keys(var.containers) : name] : r if r == "media-01"]) == 0 && !contains(values(output.addresses), "192.168.0.80")
    error_message = "The retired VM and its address are gone from the root."
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

run "rejects_old_environment" {
  command = plan
  variables {
    proxmox_endpoint = "https://192.168.0.14:8006/"
  }
  expect_failures = [var.proxmox_endpoint]
}
