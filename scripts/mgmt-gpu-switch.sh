#!/bin/bash
# Runs on the Proxmox host, detached from the VM it restarts (make mgmt-gpu-switch): a pending hardware
# change of the workstation VM only takes effect on a cold start, and the workstation cannot wait for its own
# restart. Shuts the VM down, starts it, and waits up to six minutes for the guest agent and the remote
# desktop port. When they do not answer, takes the passed-through device out of the VM and starts it again.
#
# A rollback changes the VM only, not the code: profile.gpu_mapping in the workstation's private
# terraform.tfvars still names the mapping, so the next `make mgmt-plan` shows `+ hostpci` and an apply
# would put the device back. After a rollback, set gpu_mapping to null (or remove it) before planning,
# until the cause is understood. The log says so, and the marker file below records the rollback.
#
# Answering is not enough to call the result good: on 2026-11-20 the guest booted but GNOME took the
# passed-through GPU as its primary display and remote login never opened (TASK-028). The
# admin_workstation role now writes the udev rule that prevents it.
#
# Usage: mgmt-gpu-switch.sh <vmid> <guest address>
# Log: /root/vm-<vmid>-gpu-switch.log   Rollback marker: /root/vm-<vmid>-gpu-rolled-back
set -u
vm="$1"
address="$2"
log="/root/vm-$vm-gpu-switch.log"
marker="/root/vm-$vm-gpu-rolled-back"
exec >> "$log" 2>&1
echo "== $(date -Is) cold start of VM $vm"
trap 'echo "$(date -Is) RESULT interrupted: stopped before a result (no rollback done)"' TERM INT

# Deadline-based: one agent ping can block for half a minute, so counting attempts is not a duration.
answers() {
  local end=$(( $(date +%s) + 360 ))
  while [ "$(date +%s)" -lt "$end" ]; do
    if timeout 10 qm agent "$vm" ping >/dev/null 2>&1 && timeout 2 bash -c "</dev/tcp/$address/3389" 2>/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

qm shutdown "$vm" --timeout 240 || qm stop "$vm"
if qm start "$vm" && answers; then
  echo "$(date -Is) RESULT ok: guest agent and remote desktop answer"
  qm config "$vm" | grep -E '^(cores|hostpci0|vga):'
  rm -f "$marker"
  exit 0
fi
echo "$(date -Is) RESULT rolled back: the VM did not answer within six minutes; taking hostpci0 out"
qm stop "$vm" || true
qm set "$vm" --delete hostpci0
date -Is > "$marker"
qm start "$vm"
if answers; then
  echo "$(date -Is) the VM answers again without the device"
else
  echo "$(date -Is) the VM still does not answer"
fi
echo "$(date -Is) NEXT: set profile.gpu_mapping to null in the workstation's terraform.tfvars before the next make mgmt-plan; otherwise an apply puts the device back"
exit 1
