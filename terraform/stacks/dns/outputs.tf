output "address" {
  value = split("/", var.profile.ipv4)[0]
}

output "addresses" {
  value = { for name, instance in local.instances : name => split("/", instance.ipv4)[0] }
}

# Consumed by `make dns-configure` and `make dns-hostkeys` (written to .local/, never committed). The primary
# holds the service address when both are up (the higher priority).
output "ansible_inventory" {
  value = {
    all = {
      children = {
        dns = {
          hosts = {
            for name, instance in local.instances : name => {
              ansible_host               = split("/", instance.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              proxmox_node               = instance.node
              vm_id                      = instance.vm_id
              adguard_vrrp_priority      = name == var.profile.name ? 150 : 100
            }
          }
        }
      }
    }
  }
}
