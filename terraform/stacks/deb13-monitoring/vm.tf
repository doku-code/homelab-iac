# infisical run --env=dev -- terraform -chdir=terraform/stacks/deb13-monitoring fmt
# infisical run --env=dev -- terraform -chdir=terraform/stacks/deb13-monitoring validate
# infisical run --env=dev -- terraform -chdir=terraform/stacks/deb13-monitoring plan
# infisical run --env=dev -- terraform -chdir=terraform/stacks/deb13-monitoring apply

resource "proxmox_download_file" "debian13_cloud" {
  content_type = "import"
  datastore_id = "local"
  node_name    = "pve-core"

  file_name = "debian-13-genericcloud-amd64.qcow2"

  url = "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"

  overwrite = false
}

resource "proxmox_virtual_environment_vm" "monitoring" {
  name        = "deb13-monitoring"
  description = "Prometheus and Grafana monitoring stack - managed by Terraform"

  node_name = "pve-core"
  vm_id     = 208

  tags = [
    "terraform",
    "monitoring",
    "infra"
  ]

  started = true
  on_boot = true

  stop_on_destroy = true

  # Ansible installera qemu-guest-agent ensuite.
  agent {
    enabled = true
  }

  cpu {
    cores = 2
    type  = "x86-64-v2-AES"
  }

  bios = "ovmf"
  machine = "q35"

  efi_disk {
    datastore_id      = "local-lvm"
    type              = "4m"
    pre_enrolled_keys = false
  }

  memory {
    dedicated = 4096
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    import_from  = proxmox_download_file.debian13_cloud.id

    size     = 32
    discard  = "on"
    iothread = true
  }

  scsi_hardware = "virtio-scsi-single"

  network_device {
    bridge   = "vmbr0"
    model    = "virtio"
    firewall = true
  }

  initialization {
    datastore_id = "local-lvm"

    dns {
      domain  = "home.arpa"
      servers = ["192.168.0.20"]
    }

    ip_config {
      ipv4 {
        address = "192.168.0.28/24"
        gateway = "192.168.0.20"
      }
    }

    user_account {
      username = "debian"

      keys = [
        trimspace(file("${path.module}/../../../keys/doku-lab-admin.pub"))
      ]
    }
  }

  operating_system {
    type = "l26"
  }

  serial_device {}
}
