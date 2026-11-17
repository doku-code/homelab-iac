# Bootstrap deployment runner (ADR-014, M003): one headless Debian VM beside mgmt-control-01. Applied only
# from the operator workstation (ADR-008) with the tofu@pve!mgmt token; the runner never applies this root.
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
}

# Dated Debian 13 generic cloud image, verified by Proxmox against the published SHA512SUMS.
resource "proxmox_download_file" "debian" {
  node_name          = var.profile.node
  datastore_id       = var.profile.image_datastore
  content_type       = "import"
  url                = var.image.url
  file_name          = basename(var.image.url)
  checksum           = var.image.sha512
  checksum_algorithm = "sha512"
  overwrite          = false
}

module "runner" {
  source         = "../../modules/headless-vm"
  profile        = var.profile
  image_id       = proxmox_download_file.debian.id
  tags           = ["management", "deploy-runner"]
  username       = var.admin_username
  started        = true
  on_boot        = true
  disk_discard   = "on" # thin pool shared with VM 100
  disk_ssd       = true
  ssh_public_key = coalesce(var.ssh_public_key, file("${path.module}/../../../keys/mgmt-control-01.pub"))
}
