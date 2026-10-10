# USB transition reconciliation - 2026-10-10

## Scope and status

Operator-authorized emergency maintenance, not an architecture migration.
Workstation boot recovery is live-verified; printing remains blocked before USB
enumeration. Historical [September diagnosis](workstation-start-diagnosis.md)
remains evidence of its original observation, not current hardware presence.

## Printer: no host-side enumeration

CT203 (print-server, 192.168.0.23) is running on pve-core. CUPS is active;
HLL2320D is enabled and accepting jobs, but job 63 is waiting for the printer.
The operator reports the Brother HL-L2320D powered and directly connected.

Read-only host evidence:

- `lsusb`, `lsusb -t` and sysfs show root hubs and Intel AX210 Bluetooth only;
  no Brother or alternate printer identity. `/dev/usb` is absent on the host.
- Current-boot kernel USB logs contain no printer attachment, descriptor errors,
  repeated connect/disconnect, resets or failed enumeration.
- USB ports have `disable=0`, zero over-current counters and active runtime
  status. USB controllers use xhci_hcd (USB4 NHI: thunderbolt), not VFIO.
- Idle hubs are runtime-suspended with automatic power control;
  `usbcore.autosuspend=2`. This is not evidence that autosuspend caused the
  failure. No power-management, driver-binding or kernel setting was changed.
- Guest `lpinfo -v` exposes no USB printer. Its `/dev/usb/lp0` is an empty
  mode-000 regular file, not a printer character device: the optional bind mount
  has no source device. Existing duplicated USB allowances/mounts were untouched.

No CUPS/CT restart, queue edit, new job or USB configuration change occurred.
Job 63 may print when the device returns. Physical printer/cable/port-side
testing by the operator is the next step; disconnection is not established.
Observe host enumeration before changing CT passthrough. No successful print
is claimed, and no further test job should be submitted while 63 is queued.
CT203 has no resource in the inspected local Terraform states; no import or
ownership transfer was attempted.

## Workstations: one shared mapping corrected

Live VM502 and VM601 are on pve-lab. Terraform identities and their four logical
USB references agree with live configuration; GPU, USB slots, affinity, disks
and the existing exclusivity hook remain unchanged.

| Shared mapping | Observed device | Action |
| --- | --- | --- |
| pve-lab-workstation-logitech | Logitech G Pro Wireless wired, `046d:c088` | Replace absent receiver `046d:c539` |
| pve-lab-workstation-keyboard | SteelSeries Apex 3 TKL, `1038:1622` | None |
| pve-lab-workstation-brio | Brio 300, `046d:0942` | None |
| pve-lab-workstation-scarlett | Scarlett 2i2, `1235:8210` | None |

The four peripherals are present on the same USB hub. Desired vendor/product
IDs belong to `ansible/inventories/host_vars/pve-lab.yml`; Terraform owns the VM
references, not the cluster mapping definition. The existing host role creates
missing mappings but does not reconcile changed existing mappings. Do not run
its broad host bootstrap merely to update one USB identity.

The single existing Logitech mapping was updated with a digest-guarded
`pvesh set /cluster/mapping/usb/pve-lab-workstation-logitech --map
node=pve-lab,id=046d:c088 --digest <fresh-read-digest>`. Readback matched.
VM501/502/503/601/602 share this mapping: the change applies to their common
exclusive peripheral pool, not a newly assigned private mouse. No mapping was
removed and none of the other guests was started.

VM502 started through its normal hook, guest-agent ping and OS information
succeeded (Windows 11), then graceful shutdown succeeded. Only afterward,
VM601 passed the same checks (Ubuntu 26.04.1) and was gracefully stopped.
Both boot tests passed without the previous invalid USB mapping error.
This proves boot and agent availability, not physical keyboard/mouse interaction.

## Remaining targeted Terraform review

No plan/apply or state operation was performed. Runtime Infisical credentials
were unavailable; no broad drift reconciliation is claimed. From the existing
authenticated operator shell, the following temporary Make rule reuses the
repository's Universal Auth wrapper and reviews only the two affected VMs:

```sh
make -f Makefile -f - emergency-usb-plan <<'MAKE'
.PHONY: emergency-usb-plan
emergency-usb-plan:
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) plan -input=false -target='proxmox_virtual_environment_vm.workstation["dev"]' -target='proxmox_virtual_environment_vm.workstation["ubuntu"]')
MAKE
```

Review the complete result; stop on replacement, placement changes or unrelated
drift. This is not permission to apply it. No saved plan is produced, so it
cannot accidentally replace the normal workstation apply artifact.
Manual relocation of other CTs and unrelated guest changes remain outside this
repair; historical inventory is not a current topology guarantee.

## Repository validation

Workstation Terraform format/validation passed (provider schema validation
required execution outside the local sandbox). `tests/vm-profiles.py` passed
18 isolated mocked cases. Workstation Ansible syntax, configuration/script
quality checks, changed-document links, the above Make rule dry-run and
`git diff --check` passed. Local gitleaks is unavailable; the reviewed
push-triggered quality workflow runs its existing redacted secret scan and
offline checks. Image publication remains manual-only.
