output "addresses" {
  description = "k3s node name => IPv4 address."
  value       = { for name, n in var.nodes : name => split("/", n.ipv4)[0] }
}

output "api_endpoint" {
  description = "Kubernetes API of the first server (cluster-init)."
  value       = "https://${split("/", var.nodes[local.init_node].ipv4)[0]}:6443"
}

# Consumed by `make k3s-cluster-configure` (written to .local/, never committed).
output "ansible_inventory" {
  value = {
    all = {
      children = {
        k3s_cluster = {
          vars = {
            k3s_init_node = local.init_node
          }
          hosts = {
            for name, n in var.nodes : name => {
              ansible_host               = split("/", n.ipv4)[0]
              ansible_user               = var.admin_username
              ansible_python_interpreter = "/usr/bin/python3"
              k3s_role                   = n.role
              proxmox_node               = n.node
              vm_id                      = n.vm_id
            }
          }
        }
      }
    }
  }
}

locals {
  # The first server (by name) initialises embedded etcd; later servers join it.
  init_node = sort([for name, n in var.nodes : name if n.role == "server"])[0]
}
