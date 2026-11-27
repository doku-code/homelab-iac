output "addresses" {
  value = { for name, c in var.containers : name => split("/", c.ipv4)[0] }
}

# Consumed by `make media-configure`, `make media-hostkeys` and `make media-mounts` (written to .local/, never
# committed). One host per container, named after its service; the retired VM is not in it.
output "ansible_inventory" {
  value = {
    all = {
      children = {
        media = {
          hosts = {
            for name, c in var.containers : name => {
              ansible_host               = split("/", c.ipv4)[0]
              ansible_user               = "root"
              ansible_python_interpreter = "/usr/bin/python3"
              proxmox_node               = var.node
              vm_id                      = c.vm_id
              media_service              = name
            }
          }
        }
      }
    }
  }
}
