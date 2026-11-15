#!/bin/zsh
# Hourly queue publisher: one public Short per hour, 24/7, Nov 15 16:00 - Nov 18 23:59.
# Runs every 10 minutes; review_queue.tick() publishes the oldest reviewed Short once per hour and refills to 4.
set -uo pipefail

PROJECT_DIR="/Users/FlashbangFumbles/Library/Application Support/SPECTRE Gaming Agent"
TODAY="$(/bin/date +%Y-%m-%d)"
if [[ "$TODAY" < "2026-11-15" || "$TODAY" > "2026-11-18" ]]; then
  exit 0
fi

cd "$PROJECT_DIR"
LOCK="$PROJECT_DIR/output/.publish.lock"
if ! /bin/mkdir "$LOCK" 2>/dev/null; then
  if [[ -n "$(/usr/bin/find "$LOCK" -maxdepth 0 -mmin +40 2>/dev/null)" ]]; then
    /bin/rmdir "$LOCK"; /bin/mkdir "$LOCK" || exit 0
  else
    exit 0
  fi
fi
trap '/bin/rmdir "$LOCK" 2>/dev/null' EXIT

set -a; [[ -f .env ]] && . ./.env; set +a
export SPECTRE_AUDIO_MODE=narrated PYTHONPATH=src SPECTRE_ROOT="$PROJECT_DIR"
echo "$(/bin/date '+%F %T') queue-tick"
"$PROJECT_DIR/.venv313/bin/python" -m spectre.cli queue-tick || echo "$(/bin/date '+%F %T') tick failed; will retry next run"
