#!/bin/zsh
# Safely saves your Meta credentials into both .env files. Nothing is printed or sent anywhere.
set -u
FILES=("$HOME/Documents/GTA VI/SPECTRE-Gaming-Agent-Starter/.env" "$HOME/Library/Application Support/SPECTRE Gaming Agent/.env")
printf "Paste META_APP_ID (visible): "; read APP_ID
printf "Paste META_APP_SECRET (hidden): "; read -s APP_SECRET; echo
printf "Paste META_USER_TOKEN (hidden): "; read -s USER_TOKEN; echo
for f in "${FILES[@]}"; do
  /usr/bin/grep -v '^META_' "$f" > "$f.tmp" 2>/dev/null || true
  {
    cat "$f.tmp" 2>/dev/null
    echo "META_APP_ID=$APP_ID"
    echo "META_APP_SECRET=$APP_SECRET"
    echo "META_USER_TOKEN=$USER_TOKEN"
  } > "$f"
  rm -f "$f.tmp"
  chmod 600 "$f"
  echo "Saved to $f"
done
echo "Done. Tell the assistant: done"
