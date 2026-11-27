#!/usr/bin/env bash
# Read-only state of the media containers (TASK-036), from the workstation: `make media-status`.
# Usage: media-status.sh <node> then lines "name vmid address" on standard input.
set -uo pipefail

node="$1"
port() { case "$1" in jellyfin) echo 8096;; seerr) echo 5055;; radarr) echo 7878;; sonarr) echo 8989;; prowlarr) echo 9696;; esac; }
health() { case "$1" in jellyfin) echo /health;; seerr) echo /api/v1/status;; *) echo "/$1/ping";; esac; }
remote() { ssh -o BatchMode=yes -o ConnectTimeout=5 "root@$1" "${@:2}" 2>/dev/null; }

failed=0
while read -r name vmid address; do
  unit="$(remote "$address" systemctl is-active "$name" </dev/null || true)"
  answer="$(remote "$address" curl -s -o /dev/null -m 8 -w '%{http_code}' "http://127.0.0.1:$(port "$name")$(health "$name")" </dev/null || true)"
  printf '%-9s CT %s %s  unit %-8s health HTTP %s\n' "$name" "$vmid" "$address" "${unit:-unreachable}" "${answer:-none}"
  [ "$unit" = active ] && [ "$answer" = 200 ] || failed=1
  case "$name" in
    jellyfin)
      remote "$address" 'printf "          Plex library: %s entries (%s); test area: %s; graphics device: %s\n" "$(ls /media/plex 2>/dev/null | wc -l)" "$(findmnt -no OPTIONS /media/plex | cut -d, -f1)" "$(findmnt -no OPTIONS /data/media | cut -d, -f1)" "$(ls /dev/dri/renderD128 2>/dev/null || echo absent)"' </dev/null ;;
    radarr|sonarr)
      remote "$address" 'printf "          downloads: %s entries (%s); test area: %s\n" "$(ls /downloads 2>/dev/null | wc -l)" "$(findmnt -no OPTIONS /downloads | cut -d, -f1)" "$(findmnt -no OPTIONS /data/media | cut -d, -f1)"' </dev/null ;;
  esac
done
printf 'node %s: ' "$node"
remote "$node" 'for p in /mnt/media-nas/plex /mnt/media-nas/downloads; do printf "%s %s; " "$p" "$(findmnt -no SOURCE,OPTIONS "$p" | awk "{split(\$2,o,\",\"); print \$1\" \"o[1]}" || echo "NOT MOUNTED")"; done; echo' </dev/null
exit "$failed"
