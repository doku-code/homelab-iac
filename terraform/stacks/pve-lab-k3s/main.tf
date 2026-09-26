provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = var.proxmox_insecure
}

locals {
  # One immutable image per Proxmox node/datastore, shared by its server VMs.
  image_locations = { for profile in values(var.servers) :
    "${profile.node}/${profile.image_datastore}" => profile...
  }
}

resource "proxmox_download_file" "linux" {
  for_each           = local.image_locations
  node_name          = each.value[0].node
  datastore_id       = each.value[0].image_datastore
  content_type       = "import"
  url                = var.image.url
  file_name          = "k3s-lab-${substr(var.image.sha256, 0, 16)}.qcow2"
  checksum           = var.image.sha256
  checksum_algorithm = "sha256"
  overwrite          = false
}

module "servers" {
  source         = "../../modules/headless-vm"
  for_each       = var.servers
  profile        = each.value
  tags           = ["k3s-lab"]
  image_id       = proxmox_download_file.linux["${each.value.node}/${each.value.image_datastore}"].id
  ssh_public_key = file("${path.module}/../../../keys/doku-lab-admin.pub")
}

output "ansible_inventory" {
  description = "Generate inventory from applied local state, never a second allocation list."
  value = {
    all = {
      children = {
        k3s_lab = {
          hosts = { for key, profile in var.servers : key => {
            ansible_host               = split("/", profile.ipv4)[0]
            ansible_user               = "debian"
            ansible_python_interpreter = "/usr/bin/python3"
            stage_a_hostname           = profile.name
            proxmox_node               = profile.node
            stage_a_vm_id              = profile.vm_id
          } }
        }
      }
    }
  }
}
