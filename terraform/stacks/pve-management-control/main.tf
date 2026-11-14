# API-token authentication only (PROXMOX_VE_API_TOKEN, checked by scripts/pve-auth-guard.py).
# No SSH block: import_from and image downloads use the API (bpg/proxmox v0.112.0 docs).
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

resource "proxmox_download_file" "ubuntu" {
  node_name          = var.profile.node
  datastore_id       = var.profile.image_datastore
  content_type       = "import"
  url                = var.image.url
  file_name          = "mgmt-ubuntu-${substr(var.image.sha256, 0, 16)}.qcow2"
  checksum           = var.image.sha256
  checksum_algorithm = "sha256"
  overwrite          = false
}

module "control" {
  source         = "../../modules/headless-vm"
  profile        = var.profile
  image_id       = proxmox_download_file.ubuntu.id
  tags           = ["management", "mgmt-control"]
  username       = var.admin_username
  ssh_public_key = coalesce(var.ssh_public_key, file("${path.module}/../../../keys/doku-lab-admin.pub"))
  started        = true
  on_boot        = true
  disk_discard   = "on" # return deleted guest blocks to the local-lvm thin pool
  disk_ssd       = true
  # Standalone host, no live migration: expose AVX2 for software rendering (GNOME headless, RDP, Zed).
  cpu_type = "host"
}
