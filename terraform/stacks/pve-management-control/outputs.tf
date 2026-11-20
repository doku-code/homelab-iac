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
              # Read by the admin_workstation role: keep the console adapter as GNOME's primary display.
              gpu_passthrough = var.profile.gpu_mapping != null
            }
          }
        }
      }
    }
  }
}

output "autoinstall_user_data" {
  description = "NoCloud user-data (Ubuntu autoinstall) served by `make mgmt-autoinstall-serve`."
  value = templatefile("${path.module}/templates/autoinstall.yaml.tftpl", {
    hostname        = var.profile.name
    username        = var.admin_username
    locale          = var.desktop.locale
    keyboard_layout = var.desktop.keyboard_layout
    timezone        = var.desktop.timezone
    ipv4            = var.profile.ipv4
    gateway         = var.profile.gateway
    dns_servers     = var.profile.dns_servers
    ssh_public_key  = trimspace(coalesce(var.ssh_public_key, file("${path.module}/../../../keys/doku-lab-admin.pub")))
    # Filled in by `make mgmt-autoinstall-serve` from .local/mgmt-control/ubuntu-password.
    password_hash = "@MGMT_PASSWORD_HASH@"
  })
}
