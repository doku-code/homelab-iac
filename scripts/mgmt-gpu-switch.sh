#!/bin/bash
# Runs on the Proxmox host, detached from the VM it restarts (make mgmt-gpu-switch): a pending hardware
# change of the workstation VM only takes effect on a cold start, and the workstation cannot wait for its own
# restart. Shuts the VM down, starts it, and waits for the guest agent and the remote desktop port. When they
# do not come back, takes the passed-through device out of the VM and starts it again without it.
# Usage: mgmt-gpu-switch.sh <vmid> <guest address>      Log: /root/vm-<vmid>-gpu-switch.log
set -u
vm="$1"
address="$2"
exec >> "/root/vm-$vm-gpu-switch.log" 2>&1
echo "== $(date -Is) cold start of VM $vm"

answers() {
  for _ in $(seq 1 72); do
    if qm agent "$vm" ping >/dev/null 2>&1 && timeout 2 bash -c "</dev/tcp/$address/3389" 2>/dev/null; then
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
  exit 0
fi
echo "$(date -Is) RESULT rolled back: the VM did not answer within six minutes; taking hostpci0 out"
qm stop "$vm" || true
qm set "$vm" --delete hostpci0
qm start "$vm"
if answers; then
  echo "$(date -Is) the VM answers again without the device"
else
  echo "$(date -Is) the VM still does not answer"
fi
exit 1
