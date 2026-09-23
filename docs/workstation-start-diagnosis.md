# Workstation start failure (2026-09-23)

## Confirmed failure and current blocker

All pve-lab VMs were stopped before the authorized reproduction. Starting
existing Windows workstation VM502 through `qm start 502` (including its normal
hookscript) returned 255. The Proxmox task log contains:

```text
WORKSTATION POOL: preparing VM 502
WORKSTATION POOL: hardware available for VM 502.
TASK ERROR: USB Mapping invalid (hardware probably changed): usb device '046d:c539' not found
```

Task: `UPID:pve-lab:0008D6C2:008CF70C:6AB45D72:qmstart:502:root@pam:`.
Earlier recent qmstart tasks reported the same missing USB device.

The immediate root cause is unavailable hardware required by the USB resource
mapping, not an active competing VM or a stale exclusivity lock. Live `lsusb`
shows none of the four mapped workstation peripherals:

| Mapping | Required USB ID |
| --- | --- |
| pve-lab-workstation-logitech | 046d:c539 |
| pve-lab-workstation-keyboard | 1038:1622 |
| pve-lab-workstation-brio | 046d:0942 |
| pve-lab-workstation-scarlett | 1235:8210 |

Live mappings match `ansible/inventories/host_vars/pve-lab.yml`. The live hook
matches the tag-driven template and completes its pre-start check. No
workstation arbitration lock holder was found. Whether the hub/KVM is switched
away, disconnected or unpowered cannot be determined from this evidence alone.

## Ownership and reviewed history

Terraform owns VM hardware and USB mapping references. Ansible owns resource
mappings, host VFIO setup, CPU affinity and hook installation. Terraform ignores
operational `started`, affinity and hookscript fields intentionally. The hook
discovers VMs tagged `workstation`, requests graceful shutdown of conflicts and
refuses to proceed if they cannot stop. No forced shutdown fallback exists.

Reviewed tag-discovery change `f1f23a5` and current workstation configuration.
The observed failure occurs after the hook succeeds; no evidence justifies
changing arbitration, removing required peripherals, or rebuilding VMs.

## Operator action and validation still required

Connect/power or switch the workstation USB hub/KVM to pve-lab. Confirm the
four expected IDs appear in `lsusb`. If hardware was intentionally replaced,
identify the replacement devices before changing mappings; never guess IDs.

Then, with all conflicting guests off, retry VM502 via the normal Proxmox
start mechanism, verify a successful boot and graceful shutdown. Repeat for
Linux VM601 if safe. Do not start a test while a user is using the gaming VM.
If missing peripherals must instead become optional, that is an operator
policy decision, not a silent removal of the intended workstation hardware.

No IaC fix or successful start/stop cycle is claimed yet. VM502 and VM601
remain stopped. No guest disks, VM definitions, hooks or host settings were
changed. Workstation operation remains blocked on physical USB availability.
This documented operator blocker permits the subsequent backend design phase;
it does not authorize backend deployment or state migration.
