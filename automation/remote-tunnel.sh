#!/bin/zsh
# Publishes the dashboard (view-only, passcode protected) through a free Cloudflare quick tunnel.
RUNTIME="$HOME/Library/Application Support/SPECTRE Gaming Agent"
OUTFILE="$HOME/Documents/GTA VI/Phone Dashboard Link.txt"
CF="$HOME/.spectre-bin/cloudflared"
"$CF" tunnel --no-autoupdate --url http://127.0.0.1:8765 2>&1 | while IFS= read -r line; do
  if [[ "$line" =~ 'https://[a-z0-9-]+\.trycloudflare\.com' ]]; then
    PASS="$(cat "$RUNTIME/output/remote_pass.txt" 2>/dev/null)"
    printf '%s/?k=%s\n' "$MATCH" "$PASS" > "$OUTFILE"
  fi
done
