#!/bin/zsh
# Keeps the review queue topped up. Separate lock from the publisher so long renders never delay a post.
PROJECT_DIR="/Users/FlashbangFumbles/Library/Application Support/SPECTRE Gaming Agent"
TODAY="$(/bin/date +%Y-%m-%d)"
if [[ "$TODAY" < "2026-11-15" || "$TODAY" > "2026-11-18" ]]; then exit 0; fi
cd "$PROJECT_DIR"
LOCK="$PROJECT_DIR/output/.render.lock"
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
echo "$(/bin/date '+%F %T') render-refill"
"$PROJECT_DIR/.venv313/bin/python" -m spectre.cli queue-refill || echo "$(/bin/date '+%F %T') refill failed; will retry"
