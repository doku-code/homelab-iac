#!/usr/bin/env bash
# What only root on the node may give the media containers (TASK-036); run on the node over SSH by
# `make media-mounts`, idempotent. Usage: pve-media-mounts.sh <nas> <jellyfin-id> <radarr-id> <sonarr-id>
#
#   - the NAS's Plex library and downloads, mounted read-only on the node (NFS) and passed on read-only
#   - the test area, a directory of the node that Radarr and Sonarr write and Jellyfin reads
#   - the node's graphics device for Jellyfin's hardware transcoding
#
# The NAS is never writable from here: its shares are exported read-only, mounted read-only and bound read-only.
# A container is restarted only when its mounts or devices change.
set -euo pipefail

nas="$1" jellyfin="$2" radarr="$3" sonarr="$4"
library=/mnt/media-nas/plex downloads=/mnt/media-nas/downloads area=/srv/media-test
# Unprivileged containers: their user 2000 ("media") is 102000 on the node.
owner=102000

# 1. The NAS shares. An empty mount point is made immutable so that nothing is ever written under it when the
#    NAS is away; nofail lets the node boot without the NAS.
for pair in "plex_media:$library:/mnt/tank/plex_media" "downloads:$downloads:/mnt/fastpool/downloads"; do
  IFS=: read -r _ point export <<<"$pair"
  if ! mountpoint -q "$point"; then
    mkdir -p "$point"
    chattr +i "$point" 2>/dev/null || true
  fi
  line="$nas:$export $point nfs ro,nofail,_netdev,soft,timeo=100,retrans=3,x-systemd.mount-timeout=30 0 0"
  grep -qF "$nas:$export $point " /etc/fstab || echo "$line" >>/etc/fstab
done
systemctl daemon-reload
for point in "$library" "$downloads"; do
  mountpoint -q "$point" || mount "$point"
  findmnt -no OPTIONS "$point" | tr ',' '\n' | grep -qx ro || { echo "$point is not read-only" >&2; exit 1; }
done

# 2. The test area.
mkdir -p "$area/test-movies" "$area/test-series"
chown -R "$owner:$owner" "$area"

# 3. The graphics device back to the node's own driver (it was handed whole to the retired VM).
device=0000:00:02.0
if [ ! -e /dev/dri/renderD128 ]; then
  if [ -e "/sys/bus/pci/drivers/vfio-pci/$device" ]; then
    echo "$device" >/sys/bus/pci/drivers/vfio-pci/unbind
  fi
  echo >"/sys/bus/pci/devices/$device/driver_override"
  modprobe i915
  [ -e "/sys/bus/pci/devices/$device/driver" ] || echo "$device" >/sys/bus/pci/drivers_probe
  for _ in $(seq 1 20); do [ -e /dev/dri/renderD128 ] && break; sleep 1; done
fi
[ -e /dev/dri/renderD128 ] || { echo "no /dev/dri/renderD128 on the node: Jellyfin gets no graphics device" >&2; exit 1; }

# 4. The containers. `pct set` rewrites the configuration; the container restarts only when it changed.
configure() {
  local id="$1"; shift
  local before after
  before="$(grep -E '^(mp|dev)[0-9]+:' "/etc/pve/lxc/$id.conf" | sort || true)"
  pct set "$id" "$@" >/dev/null
  after="$(grep -E '^(mp|dev)[0-9]+:' "/etc/pve/lxc/$id.conf" | sort || true)"
  if [ "$before" != "$after" ]; then
    pct reboot "$id" 2>/dev/null || { pct stop "$id" 2>/dev/null || true; pct start "$id"; }
    echo "changed: container $id restarted with its mounts"
  fi
}
render="$(pct exec "$jellyfin" -- getent group render | cut -d: -f3)"
[ -n "$render" ] || { echo "no group render in container $jellyfin (install Jellyfin first)" >&2; exit 1; }
configure "$jellyfin" -mp0 "$library,mp=/media/plex,ro=1" -mp1 "$area,mp=/data/media,ro=1" -dev0 "/dev/dri/renderD128,gid=$render,mode=0660"
for id in "$radarr" "$sonarr"; do
  configure "$id" -mp0 "$downloads,mp=/downloads,ro=1" -mp1 "$area,mp=/data/media"
done
echo "library: $(findmnt -no SOURCE "$library"), $(ls "$library" | wc -l) entries; downloads: $(findmnt -no SOURCE "$downloads"); test area: $area"
