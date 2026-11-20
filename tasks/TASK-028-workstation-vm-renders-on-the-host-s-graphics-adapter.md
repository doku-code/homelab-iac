---
id: TASK-028
title: Workstation VM renders on the host's graphics adapter
summary: VM 100 gets the Intel UHD 630 of pve-management through a resource mapping, all twelve host threads and Proxmox protection; cold start with automatic rollback.
type: task
status: in-progress
priority: medium
milestone: M001
created: 2026-11-20
updated: 2026-11-20
tags: [workstation, proxmox, gpu, performance]
depends_on: []
related: []
related_decisions: [ADR-009]
related_implementations:
  - terraform/stacks/pve-management-control/main.tf
  - terraform/stacks/pve-management-control/variables.tf
  - scripts/mgmt-gpu-switch.sh
  - ansible/roles/admin_workstation/defaults/main.yml
related_tests:
  - terraform/stacks/pve-management-control/tests/profile.tftest.hcl
tests_justification: ""
verification_commands:
  - make mgmt-check
evidence: []
---

# Workstation VM renders on the host's graphics adapter

## Goal

The operator's remote desktop on `mgmt-control-01` (VM 100) is slow because the VM has no graphics adapter:
GNOME, Zed and the browsers render on the CPU (measured 2026-11-20: Zed two to four of eight cores, GNOME
Shell more than one, about 70 % of the CPU busy with an idle desktop). Give the VM the adapter of its host.

## Context

- `pve-management` (Lenovo, i5-10500T, 6 cores / 12 threads, 16 GB) runs only this VM and has an Intel UHD 630
  that nothing uses. The adapter is alone in its IOMMU group; the IOMMU is on with the stock kernel command
  line; the host has no framebuffer console, so Proxmox can take the adapter from the host's `i915` driver
  when the VM starts. No change to the host's boot configuration, no host reboot.
- The token of this root cannot define a resource mapping; `make mgmt-gpu-mapping` does it as root over SSH
  and grants the token `PVEMappingUser` on that one mapping.
- A VM cannot wait for its own cold start: `make mgmt-gpu-switch` hands the restart to the host
  (`scripts/mgmt-gpu-switch.sh`), which takes the adapter out again when the guest agent and the remote
  desktop port do not answer within six minutes.

## What was changed

- `profile.gpu_mapping` (optional) adds `hostpci0` from a resource mapping; the virtual display (`std`) stays
  for the Proxmox console. `protection = true`. Private tfvars: 12 cores instead of 8, `gpu_mapping = "igpu"`.
- Guest: `intel-media-va-driver` and `vainfo` in the workstation role.

## Acceptance criteria

- [x] Plan changes VM 100 in place, nothing destroyed
- [ ] After the cold start the VM answers (agent, RDP) and shows the adapter (`lspci -k`: `i915`)
- [ ] GNOME Shell and Zed render on the adapter (CPU use of an idle desktop measured again)
- [ ] Whether the remote desktop server encodes on the adapter: observed and recorded

## Verification

```
make mgmt-check
ssh root@192.168.0.10 tail /root/vm-100-gpu-switch.log
lspci -k | grep -A3 -i vga; glxinfo -B | grep -i renderer; vulkaninfo --summary | grep deviceName
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| terraform/stacks/pve-management-control/tests/profile.tftest.hcl | No passthrough by default; with `gpu_mapping`: one device from the mapping, no raw device ID, console display kept, VM protected | `make mgmt-check` | PASS 2026-11-20 (7 runs) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Resource mapping | `igpu`: `node=pve-management,path=0000:00:02.0,id=8086:9bc8,subsystem-id=17aa:316a,iommugroup=0`; token may use it | `make mgmt-gpu-mapping` | 2026-11-20 |
| Plan | `0 to add, 1 to change, 0 to destroy`: `protection false -> true`, `cores 8 -> 12`, `+ hostpci0 mapping=igpu` | `make mgmt-plan`, plan 93660126… | 2026-11-20 |
| Apply | Applied without restart (`reboot_after_update = false`): protection active, cores and `hostpci0` pending | `qm pending 100` | 2026-11-20 |
| State copy | Copy of the state from before the apply in `.local/mgmt-tfstate-before-gpu-2026-11-20` | | 2026-11-20 |
| Cold start | not verified yet | `/root/vm-100-gpu-switch.log` on the host | |

## Completion summary

In progress. Remaining: read `/root/vm-100-gpu-switch.log` on `pve-management` (`RESULT ok` or
`RESULT rolled back`). If ok: check the three commands under Verification, measure the CPU use of the idle
desktop, record it here and complete the task. If rolled back: the VM runs without the adapter and
`make mgmt-plan` shows `hostpci0` as a difference; set `gpu_mapping` to null in the private tfvars until the
cause is understood (host journal around the start: `journalctl -b | grep -i -E 'vfio|i915|DMAR'`).
Manual way back at any time: Proxmox interface, VM 100, Hardware, remove the PCI device, shut down and start.
