#!/bin/sh
# Contribution counts of one Forgejo account for the grid of its profile page, private repositories included.
# Runs inside Forgejo's container, every ten minutes, from a cron job of the NAS (install-theme.py).
#
# Forgejo's own heatmap shows a visitor the public activity only. This counts the commits of every repository
# that carry the account's name or address, and publishes dates and counts, nothing else: no repository,
# branch, hash, message or address leaves the container.
#
# It writes the file the operator's page script already reads (custom/public/assets/js/doku-code-contributions.js),
# in the same format as the operator's first generator, which took minutes for one run: this one reads each
# repository once and counts in a single pass, and counts a commit once however many repositories hold it.
#
# usage: contributions.sh [username]     more names or addresses, one per line: custom/scripts/contributions.identities
set -eu

USERNAME="${1:-doku-code}"
CUSTOM="${GITEA_CUSTOM:-/var/lib/gitea/custom}"
APP_INI="${GITEA_APP_INI:-$CUSTOM/conf/app.ini}"
OUTPUT="$CUSTOM/public/assets/aymerick/contributions-$USERNAME.json"
DAYS=371
export TZ="${CONTRIBUTIONS_TIMEZONE:-America/Toronto}"

# Where the repositories are: [repository] ROOT of app.ini, else Forgejo's default.
ROOT="$(awk -F= '/^\[/ { section = $0 } section == "[repository]" && $1 ~ /^[ \t]*ROOT[ \t]*$/ { sub(/^[^=]*=[ \t]*/, ""); print; exit }' "$APP_INI" 2>/dev/null || true)"
[ -d "$ROOT" ] || ROOT=/var/lib/gitea/git/repositories
[ -d "$ROOT" ] || { echo "contributions: no repository directory" >&2; exit 1; }

# Who counts as the account: its name, the address Forgejo holds for it, and what the operator lists beside this script.
IDENTITIES="$USERNAME
$(forgejo admin user list 2>/dev/null | awk -v user="$USERNAME" '$2 == user { print $3 }' || true)
$(cat "$CUSTOM/scripts/contributions.identities" 2>/dev/null || true)"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT HUP INT TERM

find "$ROOT" -mindepth 2 -maxdepth 2 -type d -name '*.git' | while IFS= read -r repository; do
  timeout 120 git -c safe.directory='*' -C "$repository" log --all --since="$DAYS days ago" \
    --date=format-local:%Y-%m-%d --format='%H%x09%ad%x09%an%x09%ae%x09%cn%x09%ce' 2>/dev/null || true
done | awk -F '\t' -v identities="$IDENTITIES" '
  BEGIN { n = split(identities, list, "\n"); for (i = 1; i <= n; i++) if (list[i] != "") wanted[tolower(list[i])] = 1 }
  !seen[$1]++ && (tolower($3) in wanted || tolower($4) in wanted || tolower($5) in wanted || tolower($6) in wanted) { count[$2]++ }
  END { for (day in count) print day, count[day] }' | sort > "$work/counts"

awk -v user="$USERNAME" -v now="$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
  { days[NR] = $1; counts[NR] = $2; total += $2 }
  END {
    printf "{\n  \"username\": \"%s\",\n  \"generated_at\": \"%s\",\n  \"total\": %d,\n  \"days\": [\n", user, now, total
    for (i = 1; i <= NR; i++) printf "    { \"date\": \"%s\", \"count\": %d }%s\n", days[i], counts[i], (i < NR ? "," : "")
    printf "  ]\n}\n"
  }' "$work/counts" > "$work/json"

# Replaced in one step, so a page never reads half a file.
mkdir -p "$(dirname "$OUTPUT")"
cp "$work/json" "$OUTPUT.new"
mv "$OUTPUT.new" "$OUTPUT"
echo "contributions: $(wc -l < "$work/counts") days written to $OUTPUT"
