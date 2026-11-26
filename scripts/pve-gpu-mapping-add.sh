#!/usr/bin/env bash
# Runs ON a Proxmox node (fed over SSH by `make media-gpu-mapping`): adds this node's graphics adapter to an
# existing PCI resource mapping, keeping the entries of the other nodes. No permission is created or changed.
# Refuses a device that shares its IOMMU group. Usage: pve-gpu-mapping-add.sh <mapping> <pci-address> <description>
set -euo pipefail

mapping="${1:?mapping name}"
device="${2:?PCI address, e.g. 0000:00:02.0}"
description="${3:?description}"
[[ "$mapping" =~ ^[a-z][a-z0-9-]*$ ]] || { echo "refused: bad mapping name" >&2; exit 2; }
[[ "$device" =~ ^[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]$ ]] || { echo "refused: bad PCI address" >&2; exit 2; }

sys="/sys/bus/pci/devices/$device"
[ -d "$sys" ] || { echo "$device does not exist on $(hostname)" >&2; exit 1; }
[ "$(ls "$sys/iommu_group/devices" | wc -l)" = 1 ] || { echo "$device shares its IOMMU group with other devices" >&2; exit 1; }
id="$(cut -c3- "$sys/vendor"):$(cut -c3- "$sys/device")"
sub="$(cut -c3- "$sys/subsystem_vendor"):$(cut -c3- "$sys/subsystem_device")"
group="$(basename "$(readlink "$sys/iommu_group")")"
entry="node=$(hostname),path=$device,id=$id,subsystem-id=$sub,iommugroup=$group"

mapfile -t current < <(pvesh get "/cluster/mapping/pci/$mapping" --output-format json | python3 -c 'import json, sys; print("\n".join(json.load(sys.stdin)["map"]))')
for line in "${current[@]}"; do
  if [[ "$line" == *"node=$(hostname),"* ]]; then
    echo "$mapping: $(hostname) is already mapped ($line)"
    exit 0
  fi
done
arguments=()
for line in "${current[@]}"; do arguments+=(--map "$line"); done
pvesh set "/cluster/mapping/pci/$mapping" "${arguments[@]}" --map "$entry" --description "$description"
pvesh get "/cluster/mapping/pci/$mapping" --output-format json
