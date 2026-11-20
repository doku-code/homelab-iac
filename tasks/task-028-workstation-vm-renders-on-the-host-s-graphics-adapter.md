---
title: TASK-028 — Workstation VM renders on the host's graphics adapter
description: VM 100 gets the Intel UHD 630 of pve-management through a resource mapping, all twelve host threads and Proxmox protection; cold start with automatic rollback.
published: true
tags:
- task
- completed
- workstation
- proxmox
- gpu
- performance
editor: markdown
date: '2026-11-20T00:00:00.000Z'
dateCreated: '2026-11-20T00:00:00.000Z'
---

# TASK-028 — Workstation VM renders on the host's graphics adapter

> **ID:** TASK-028 · **Type:** task · **Status:** completed · **Updated:** 2026-11-20 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-028-workstation-vm-renders-on-the-host-s-graphics-adapter.md)

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
- After the incident below: the role writes `/etc/udev/rules.d/61-mutter-primary-gpu.rules` when the
  inventory says `gpu_passthrough` (new host variable of the `ansible_inventory` output, from
  `profile.gpu_mapping`) and removes it otherwise; the playbook stops when the inventory has no such value.
  Handlers in file order: udev reload and trigger, restart GDM, restart remote login.
- `scripts/mgmt-gpu-switch.sh`: waits six minutes by the clock (one agent ping can block 30 s, so 72
  attempts lasted far longer), logs an interruption, leaves a rollback marker on the host and says that
  `gpu_mapping` must be set to null in the private tfvars after a rollback.

## Incident at the first cold start (2026-11-20)

- Symptoms: the VM started (23:05) and Ubuntu booted, but the Proxmox console stayed frozen on the splash
  screen and remote login timed out waiting for GDM, so port 3389 never opened: no RDP, the workstation
  looked dead. The guest agent did not answer either while the host script waited.
- Cause: GNOME (mutter) chose the passed-through Intel GPU (`card1`, `i915`) as its primary display. No
  screen is attached to it, so the login screen was drawn where nobody could see it, and remote login,
  which waits for GDM's session, never started.
- Fix (by the operator, on the VM): the udev rule
  `SUBSYSTEM=="drm", KERNEL=="card[0-9]*", DRIVERS=="bochs-drm", TAG+="mutter-device-preferred-primary"`
  in `/etc/udev/rules.d/61-mutter-primary-gpu.rules`, `udevadm trigger --subsystem-match=drm --action=add`,
  restart of GDM, then of gnome-remote-desktop. GDM's log: `GPU /dev/dri/card0 selected primary given udev
  rule`; Thincast connects again. The rule is now in the role (identical bytes, so a run on this VM
  changes nothing and restarts nothing).
- The automatic rollback did not happen: its wait counted attempts instead of time, and its systemd unit was
  stopped at 23:13:40 before a result was logged (log: only the start line). Fixed as described above.

## Acceptance criteria

- [x] Plan changes VM 100 in place, nothing destroyed
- [x] After the cold start the VM answers (agent, RDP) and shows the adapter (`lspci -k`: `i915`), with the
  udev rule set by hand
- [x] GNOME Shell and Zed render on the adapter (CPU use of an idle desktop measured again)
- [x] Whether the remote desktop server encodes on the adapter: observed and recorded
- [x] The role's rule reaches the VM through `make mgmt-configure` (needs the refreshed inventory output)

## Verification

```
make mgmt-check
ssh root@192.168.0.10 tail /root/vm-100-gpu-switch.log
lspci -k | grep -A3 -i vga; glxinfo -B | grep -i renderer; vulkaninfo --summary | grep deviceName
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| terraform/stacks/pve-management-control/tests/profile.tftest.hcl | No passthrough by default; with `gpu_mapping`: one device from the mapping, no raw device ID, console display kept, VM protected; inventory `gpu_passthrough` false/true | `make mgmt-check` | PASS 2026-11-20 (7 runs) |
| tests/mgmt-control.py | udev rule content; written with a GPU, removed without; no role default for the flag; handler order udev, GDM, remote login; playbook takes the flag from the inventory and stops without it; output derives it from `gpu_mapping` | `make mgmt-check` | PASS 2026-11-20 |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Resource mapping | `igpu`: `node=pve-management,path=0000:00:02.0,id=8086:9bc8,subsystem-id=17aa:316a,iommugroup=0`; token may use it | `make mgmt-gpu-mapping` | 2026-11-20 |
| Plan | `0 to add, 1 to change, 0 to destroy`: `protection false -> true`, `cores 8 -> 12`, `+ hostpci0 mapping=igpu` | `make mgmt-plan`, plan 93660126… | 2026-11-20 |
| Apply | Applied without restart (`reboot_after_update = false`): protection active, cores and `hostpci0` pending | `qm pending 100` | 2026-11-20 |
| State copy | Copy of the state from before the apply in `.local/mgmt-tfstate-before-gpu-2026-11-20` | | 2026-11-20 |
| Cold start | Failed as described under Incident; recovered by hand with the udev rule | `/root/vm-100-gpu-switch.log`, host journal | 2026-11-20 |
| Adapters in the guest | `00:01.0` bochs-drm (`card0`, primary), `06:10.0` UHD 630 i915 (`card1`, `renderD128`); GNOME: `GPU /dev/dri/renderD128 selected as primary` for rendering | `lspci -k`, journal | 2026-11-20 |
| CPU use | Before: load 4–5, Zed 187–400 %, GNOME Shell 104–129 %, about 70 % of 8 cores busy. After: load 0.5–0.7 with 12 cores, Zed about 58 %, GNOME Shell about 5 %, gnome-remote-desktop about 6 % | `top`, `uptime` | 2026-11-20 |
| Output apply | Plan 07e9c06a…: no resource change, `ansible_inventory` gains `gpu_passthrough = true`; `Apply complete! Resources: 0 added, 0 changed, 0 destroyed` | `make mgmt-apply` | 2026-11-20 |
| Configuration | `ok=45 changed=0 failed=0 skipped=10`; rule task `ok` (identical to the hand-made file), removal task skipped, no handler ran: GDM and remote login not restarted | `make mgmt-configure`, `.local/mgmt-configure-2026-11-20.log` | 2026-11-20 |
| Remote desktop encoding | gnome-remote-desktop: `[HWAccel.VAAPI] Successfully initialized VAAPI 1.23 with vendor: Intel iHD`, Vulkan initialized; the client accepts H.264 (AVC444/AVC420). Encoding on the adapter is therefore available; per-frame use was not measured | journal | 2026-11-20 |

## Completion summary

Completed 2026-11-20. VM 100 renders on the host's Intel UHD 630 (12 cores, Proxmox protection); the console
adapter stays GNOME's primary display through the role's udev rule, which `make mgmt-configure` confirms
without restarting anything. The first cold start failed (see Incident) and was recovered by hand. Load went
from 4–5 to under 1. After a rollback by `make mgmt-gpu-switch`, set `gpu_mapping` to null in the private
tfvars before planning.
