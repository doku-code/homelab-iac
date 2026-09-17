locals {
  workstation_node      = "pve-lab"
  workstation_datastore = "lab-vms"

  workstation_profile = {
    cpu_type = "host"
    sockets  = 1
    cores    = 16

    memory  = 16384
    balloon = 0

    tags = [
      "terraform",
      "workstation",
    ]
  }

  workstation_templates = {
    win11 = {
      vm_id = 9101
    }

    ubuntu26 = {
      vm_id = 8101
    }

    fedora44 = {
      vm_id = 8200
    }
  }

  workstation_vms = {
    game = {
      vm_id    = 501
      name     = "w11-game"
      template = null

      tags = [
        "guest",
        "windows",
        "nvidia",
        "gaming",
      ]

      os_type = "win11"
      machine = "pc-q35-11.0+pve2"

      disk_size    = 500
      disk_discard = "on"
      disk_ssd     = true

      mac_address = "BC:24:11:F6:9C:A5"

      boot_order = ["scsi0", "ide2", "net0"]
      cdrom      = true
      tpm        = true

      agent_enabled = true

      smbios_uuid = "85d144d0-71cc-465f-8897-7130cb835dec"
    }

    dev = {
      vm_id    = 502
      name     = "w11-dev"
      template = null

      tags = [
        "guest",
        "windows",
        "nvidia",
        "dev",
      ]

      os_type = "win11"
      machine = "pc-q35-11.0+pve2"

      disk_size    = 160
      disk_discard = "on"
      disk_ssd     = true

      mac_address = "BC:24:11:C2:E8:C2"

      boot_order = ["scsi0"]
      cdrom      = false
      tpm        = true

      agent_enabled = true

      smbios_uuid = "b2503b41-5c2a-4b37-98ee-387ac4b2dc71"
    }

    school = {
      vm_id    = 503
      name     = "w11-school"
      template = null

      tags = [
        "guest",
        "windows",
        "nvidia",
        "school",
      ]

      os_type = "win11"
      machine = "pc-q35-11.0+pve2"

      disk_size    = 160
      disk_discard = "on"
      disk_ssd     = true

      mac_address = "BC:24:11:DF:B6:E4"

      boot_order = ["scsi0"]
      cdrom      = false
      tpm        = true

      agent_enabled = true

      smbios_uuid = "fe65e177-9e9c-4c71-9a5f-603d6c8cea95"
    }

    ubuntu = {
      vm_id    = 601
      name     = "u26-dev"
      template = null

      tags = [
        "guest",
        "linux",
        "nvidia",
        "dev",
      ]

      os_type = "l26"
      machine = "q35"

      disk_size    = 64
      disk_discard = "on"
      disk_ssd     = false

      mac_address = "BC:24:11:17:90:1C"

      boot_order = ["scsi0", "ide2", "net0"]
      cdrom      = true
      tpm        = false

      agent_enabled = true

      smbios_uuid = "bc227950-a800-4065-8752-142e24edb5ee"
    }

    fedora = {
      vm_id    = 602
      name     = "f44-dev"
      template = null

      tags = [
        "guest",
        "linux",
        "nvidia",
        "dev",
      ]

      os_type = "l26"
      machine = "q35"

      disk_size    = 32
      disk_discard = "ignore"
      disk_ssd     = false

      mac_address = "BC:24:11:F7:F5:59"

      boot_order = ["scsi0", "ide2", "net0"]
      cdrom      = true
      tpm        = false

      # Fedora n'a actuellement pas "agent: 1".
      # On pourra le passer à true après installation
      # de qemu-guest-agent par Ansible.
      agent_enabled = false

      smbios_uuid = "9e19977d-2879-468a-9d7c-8bf3948221f3"
    }
  }
}
