#!/bin/zsh
# Invoked by launchd every three hours from 10:00 through 19:00 in this Mac's time zone.
# This campaign runs from 15–18 November 2026.
set -euo pipefail

PROJECT_DIR="/Users/FlashbangFumbles/Documents/GTA VI/SPECTRE-Gaming-Agent-Starter"
TODAY="$(/bin/date +%Y-%m-%d)"
if [[ "$TODAY" < "2026-11-15" || "$TODAY" > "2026-11-18" ]]; then
  exit 0
fi
HOUR="$(/bin/date +%H)"
case "$HOUR" in
  10|11) SLOT="morning" ;;
  13) SLOT="afternoon" ;;
  16) SLOT="evening" ;;
  19) SLOT="night" ;;
  *) exit 0 ;;
esac

cd "$PROJECT_DIR"
export SPECTRE_AUDIO_MODE=narrated
exec "$PROJECT_DIR/.venv313/bin/python" -m spectre.cli daily --slot "$SLOT" --visibility public
