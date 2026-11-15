#!/bin/zsh
# Keep this Mac awake while the GTA VI pre-launch publishing campaign runs.
set -euo pipefail

END_EPOCH="$(/bin/date -j -f '%Y-%m-%d %H:%M:%S' '2026-11-18 20:00:00' '+%s')"
NOW_EPOCH="$(/bin/date '+%s')"
SECONDS_REMAINING=$(( END_EPOCH - NOW_EPOCH ))

if (( SECONDS_REMAINING > 0 )); then
  exec /usr/bin/caffeinate -im -t "$SECONDS_REMAINING"
fi
