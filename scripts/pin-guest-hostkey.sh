#!/usr/bin/env bash
# Pin a new guest's SSH host key only after two independent channels agree:
#   1. the key the guest presents on the network (ssh-keyscan), and
#   2. the key read out-of-band from the guest's own disk on its Proxmox node (read-only loop device +
#      debugfs -c, over the workstation's root SSH to the node).
# Then the known_hosts entry for the guest IP is replaced (a rebuilt VM legitimately gets a new key).
# Usage: scripts/pin-guest-hostkey.sh <proxmox-node-ip> <vmid> <guest-ip>
set -euo pipefail

node="${1:?proxmox node IP}"
vmid="${2:?VMID}"
guest="${3:?guest IP}"
known_hosts="${KNOWN_HOSTS:-$HOME/.ssh/known_hosts}"

# New cluster only (AGENTS.md): never the old environment 192.168.0.14.
case "$node" in 192.168.0.10|192.168.0.11|192.168.0.12|192.168.0.16) ;; *) echo "refused: $node is not a doku-lab node" >&2; exit 2;; esac
[[ "$vmid" =~ ^[0-9]{3,4}$ ]] || { echo "refused: bad VMID $vmid" >&2; exit 2; }
[[ "$guest" =~ ^192\.168\.0\.[0-9]{1,3}$ ]] || { echo "refused: bad guest IP $guest" >&2; exit 2; }

network_key=""
for _ in $(seq 1 60); do
  network_key="$(ssh-keyscan -T 5 -t ed25519 "$guest" 2>/dev/null | awk '$2 == "ssh-ed25519" {print $2" "$3; exit}')"
  [ -n "$network_key" ] && break
  sleep 5
done
[ -n "$network_key" ] || { echo "no SSH host key from $guest after 5 minutes" >&2; exit 1; }
sleep 10 # let the guest flush the key cloud-init just generated

disk_key="$(ssh -o BatchMode=yes "root@$node" bash -s -- "$vmid" <<'REMOTE'
set -euo pipefail
vmid="$1"
volume="$(qm config "$vmid" | sed -n 's/^scsi0: \([^,]*\).*/\1/p')"
dev="$(pvesm path "$volume")"
loop="$(losetup -r -P -f --show "$dev")"
trap 'losetup -d "$loop"' EXIT
debugfs -c -R "cat /etc/ssh/ssh_host_ed25519_key.pub" "${loop}p1" 2>/dev/null | awk '$1 == "ssh-ed25519" {print $1" "$2; exit}'
REMOTE
)"
[ -n "$disk_key" ] || { echo "could not read the host key from VM $vmid's disk on $node" >&2; exit 1; }

if [ "$network_key" != "$disk_key" ]; then
  echo "MISMATCH for $guest: network key differs from the key on VM $vmid's disk; not pinned" >&2
  exit 1
fi

touch "$known_hosts"
ssh-keygen -R "$guest" -f "$known_hosts" >/dev/null 2>&1 || true
printf '%s %s\n' "$guest" "$network_key" >> "$known_hosts"
printf 'pinned %s %s\n' "$guest" "$(printf '%s %s\n' "$guest" "$network_key" | ssh-keygen -lf - | awk '{print $2}')"
