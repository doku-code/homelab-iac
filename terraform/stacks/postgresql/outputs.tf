output "addresses" {
  description = "Member name => IPv4 address."
  value       = { for name, n in var.nodes : name => split("/", n.ipv4)[0] }
}

output "virtual_ip" {
  description = "Address applications connect to (port 5432, TLS required)."
  value       = var.virtual_ip
}

# Consumed by `make postgresql-configure` and `make postgresql-hostkeys` (written to .local/, never committed).
output "ansible_inventory" {
  value = {
    all = {
      children = {
        postgresql = {
          vars = {
            patroni_virtual_ip = var.virtual_ip
          }
          hosts = {
            for name, n in var.nodes : name => {
              ansible_host               = split("/", n.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              patroni_failover_priority  = n.failover_priority
              proxmox_node               = n.node
              vm_id                      = n.vm_id
            }
          }
        }
      }
    }
  }
}
