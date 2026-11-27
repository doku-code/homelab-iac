#!/usr/bin/env bash
# One archive of what the media services hold (TASK-036), written on the workstation: `make media-backup`.
# Usage: media-backup.sh <directory> then lines "name vmid address" on standard input.
#
#   jellyfin   a consistent copy of its SQLite databases (sqlite3 .backup) and its configuration
#   seerr      its settings file; a dump of its PostgreSQL database
#   radarr, sonarr, prowlarr   a dump of their two PostgreSQL databases each
#
# The dumps are made in the containers, with the sign-in each application already has: no other host may read
# those databases. Metadata images and the transcoding cache are not saved: Jellyfin rebuilds them.
# The platform has no PostgreSQL backups yet (M012); until then this archive is the copy of these databases.
set -euo pipefail

directory="$1"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
umask 077
mkdir -p "$directory" "$work/media-$stamp"

while read -r name vmid address; do
  out="$work/media-$stamp/$name"
  mkdir -p "$out"
  case "$name" in
    jellyfin)
      ssh -o BatchMode=yes "root@$address" 'set -e; t=$(mktemp -d); for f in /var/lib/jellyfin/data/*.db; do sqlite3 "$f" ".backup $t/$(basename "$f").copy"; done; tar -C / -cf - etc/jellyfin var/lib/jellyfin/root var/lib/jellyfin/plugins -C "$t" . 2>/dev/null; rm -rf "$t"' </dev/null >"$out/jellyfin.tar" ;;
    seerr)
      ssh -o BatchMode=yes "root@$address" 'tar -C /var/lib/seerr -cf - settings.json 2>/dev/null' </dev/null >"$out/settings.tar"
      ssh -o BatchMode=yes "root@$address" 'set -a; . /etc/media/seerr.env; PGPASSWORD="$DB_PASS" PGSSLMODE=require pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME"' </dev/null >"$out/seerr.dump" ;;
    radarr|sonarr|prowlarr)
      for database in "$name" "${name}_log"; do
        ssh -o BatchMode=yes "root@$address" "set -a; . /etc/media/$name.env; p=\$(echo $name | tr a-z A-Z); eval \"PGPASSWORD=\\\$\${p}__POSTGRES__PASSWORD\"; eval \"host=\\\$\${p}__POSTGRES__HOST\"; export PGPASSWORD; PGSSLMODE=require pg_dump -h \"\$host\" -U $name -Fc $database" </dev/null >"$out/$database.dump"
      done ;;
  esac
done
find "$work/media-$stamp" -type f -size 0 -print | sed 's/^/EMPTY: /' | tee "$work/empty"
tar -C "$work" -cf - "media-$stamp" | zstd -q -T0 >"$directory/media-$stamp.tar.zst"
ls -l "$directory/media-$stamp.tar.zst"
tar -I zstd -tvf "$directory/media-$stamp.tar.zst" | awk '{print $3, $6}' | grep -v '/$'
[ ! -s "$work/empty" ]
