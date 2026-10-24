# Compatibility input: fail closed on stale private passthrough profiles.
variable "hardware_profiles" {
  description = "Retired passthrough input; only empty headless overrides are accepted."
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
      try(profile.gpu == false && length(profile.usb_mappings) == 0, false)
    ])
    error_message = "Workstation passthrough is retired; gpu must be false and usb_mappings empty."
  }
}
