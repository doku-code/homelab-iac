resource "proxmox_download_file" "debian13_cloud" {
  content_type = "import"
  datastore_id = "local"
  node_name    = "pve-lab"

  file_name = "debian-13-genericcloud-amd64.qcow2"

  url = "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"

  overwrite = false
}


resource "proxmox_virtual_environment_vm" "terraform_test" {
  name        = "terraform-test"
  description = "Disposable VM managed by Terraform"
  tags        = ["terraform", "test"]

  node_name = "pve-lab"

  started = true
  on_boot = false

  stop_on_destroy = true

  agent {
    enabled = false
  }

  cpu {
    cores = 2
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = 2048
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    import_from  = proxmox_download_file.debian13_cloud.id
    size         = 20
    discard      = "on"
  }

  scsi_hardware = "virtio-scsi-single"

  network_device {
    bridge   = "vmbr0"
    model    = "virtio"
    firewall = true
  }

  initialization {
    datastore_id = "local-lvm"

    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    user_account {
      username = "terraform"

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


output "terraform_test_vm_id" {
  description = "VM ID automatically assigned by Proxmox"
  value       = proxmox_virtual_environment_vm.terraform_test.vm_id
}
