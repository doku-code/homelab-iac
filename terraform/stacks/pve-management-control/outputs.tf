output "address" {
  description = "Management VM IPv4 address (no prefix)."
  value       = split("/", var.profile.ipv4)[0]
}

output "ansible_inventory" {
  description = "Inventory for ansible/playbooks/configure-mgmt-control.yml, derived from the same allocation."
  value = {
    all = {
      children = {
        mgmt_control = {
          hosts = {
            (var.profile.name) = {
              ansible_host = split("/", var.profile.ipv4)[0]
              ansible_user = var.admin_username
              vm_id        = var.profile.vm_id
            }
          }
        }
      }
    }
  }
}
