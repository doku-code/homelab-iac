# Media services (TASK-036): one unprivileged container per service on pve-infra (containers.tf), outside k3s by
# the operator's choice. The first version, one Compose VM (media-01, VM 380), was deleted on 2026-11-27.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

# The retired VM's cloud image: the automation's token may not delete files of a datastore (Datastore.Allocate
# is not in its role, on purpose), so the root only forgets it; root on the node removed the file itself.
removed {
  from = proxmox_download_file.debian
  lifecycle {
    destroy = false
  }
}
