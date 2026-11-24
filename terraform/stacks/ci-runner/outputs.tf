output "address" {
  value = split("/", var.profile.ipv4)[0]
}

# Consumed by `make ci-runner-configure` and `make ci-runner-hostkeys` (written to .local/, never committed).
output "ansible_inventory" {
  value = {
    all = {
      children = {
        ci_runner = {
          hosts = {
            (var.profile.name) = {
              ansible_host               = split("/", var.profile.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              proxmox_node               = var.profile.node
              vm_id                      = var.profile.vm_id
            }
          }
        }
      }
    }
  }
}
