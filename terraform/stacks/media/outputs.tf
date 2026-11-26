output "address" {
  value = split("/", var.profile.ipv4)[0]
}

# Consumed by `make media-configure` and `make media-hostkeys` (written to .local/, never committed).
output "ansible_inventory" {
  value = {
    all = {
      children = {
        media = {
          hosts = {
            (var.profile.name) = {
              ansible_host               = split("/", var.profile.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              proxmox_node               = var.profile.node
              vm_id                      = var.profile.vm_id
              media_gpu                  = var.profile.gpu_mapping != null
            }
          }
        }
      }
    }
  }
}
