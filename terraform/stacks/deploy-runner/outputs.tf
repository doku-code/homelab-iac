output "address" {
  description = "Runner IPv4 address (no prefix)."
  value       = split("/", var.profile.ipv4)[0]
}

output "ansible_inventory" {
  description = "Inventory for ansible/playbooks/configure-deploy-runner.yml, derived from the same allocation."
  value = {
    all = {
      children = {
        deploy_runner = {
          hosts = {
            (var.profile.name) = {
              ansible_host               = split("/", var.profile.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              vm_id                      = var.profile.vm_id
              proxmox_node               = var.profile.node
            }
          }
        }
      }
    }
  }
}
