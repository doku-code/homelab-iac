locals {
  # Preserve the existing devices and their order unless explicitly overridden.
  default_hardware = {
    gpu = true
    usb_mappings = [
      "pve-lab-workstation-logitech",
      "pve-lab-workstation-keyboard",
      "pve-lab-workstation-brio",
      "pve-lab-workstation-scarlett",
    ]
  }
}

variable "hardware_profiles" {
  description = "Optional per-workstation hardware capabilities; never prepares host mappings."
  type = map(object({
    gpu          = bool
    usb_mappings = list(string)
  }))
  default  = {}
  nullable = false
  validation {
    condition = alltrue([
      for name, profile in var.hardware_profiles :
      contains(["game", "dev", "school", "ubuntu", "fedora"], name) &&
      profile.gpu != null && profile.usb_mappings != null &&
      try(length(distinct(profile.usb_mappings)) == length(profile.usb_mappings) && alltrue([
        for mapping in profile.usb_mappings : contains(local.default_hardware.usb_mappings, mapping)
      ]), false)
    ])
    error_message = "Use existing workstation names, a GPU boolean and unique existing USB mapping names."
  }
}
