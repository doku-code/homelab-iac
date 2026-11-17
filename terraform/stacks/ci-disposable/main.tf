# Disposable proof resource for M003: a stopped VM with a 1 GiB empty disk and no NIC, inside the
# Proxmox pool ci-disposable, the only place the runner's deploy-runner@pve!ci token may create guests.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_virtual_environment_vm" "probe" {
  node_name   = var.node
  vm_id       = var.vm_id
  name        = "ci-disposable-${var.vm_id}"
  description = "Disposable CI probe. Managed by the deployment runner (homelab-iac terraform/stacks/ci-disposable); safe to destroy."
  pool_id     = var.pool
  # No tags: Proxmox checks tag permissions on /vms/<id> without the pool (GuestHelpers::assert_tag_permissions),
  # so a pool-scoped token cannot create a tagged guest. The pool, name and description identify the probe.
  started             = false
  on_boot             = false
  reboot_after_update = false
  scsi_hardware       = "virtio-scsi-single"

  cpu {
    cores = 1
  }
  memory {
    dedicated = 128
  }
  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    file_format  = "raw"
    size         = 1
  }
  operating_system {
    type = "l26"
  }
}

output "probe" {
  value = {
    vm_id = proxmox_virtual_environment_vm.probe.vm_id
    node  = proxmox_virtual_environment_vm.probe.node_name
    pool  = proxmox_virtual_environment_vm.probe.pool_id
  }
}
