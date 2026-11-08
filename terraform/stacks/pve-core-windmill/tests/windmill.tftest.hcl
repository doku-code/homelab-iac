mock_provider "proxmox" { alias = "root" }
variables {
  ctid = 9999
}
run "isolated_service" {
  command = plan
  assert {
    condition = (
      proxmox_virtual_environment_container.windmill.node_name == "pve-core" &&
      proxmox_virtual_environment_container.windmill.initialization[0].hostname == "windmill" &&
      proxmox_virtual_environment_container.windmill.unprivileged &&
      proxmox_virtual_environment_container.windmill.features[0].keyctl &&
      proxmox_virtual_environment_container.windmill.features[0].nesting &&
      !proxmox_virtual_environment_container.windmill.features[0].fuse &&
      !proxmox_virtual_environment_container.windmill.features[0].mknod &&
      proxmox_virtual_environment_container.windmill.initialization[0].ip_config[0].ipv4[0].address == "dhcp"
    )
    error_message = "Dedicated unprivileged Docker CT boundary changed."
  }
}
