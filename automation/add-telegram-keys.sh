#!/bin/zsh
# Saves Telegram bot credentials into both .env files and finds your chat id automatically.
RT="$HOME/Library/Application Support/SPECTRE Gaming Agent"
FILES=("$HOME/Documents/GTA VI/SPECTRE-Gaming-Agent-Starter/.env" "$RT/.env")
printf "Paste the bot token from BotFather (hidden), then press Enter: "; read -s TOKEN; echo
export TOKEN
"$RT/.venv313/bin/python" - <<'PY' || exit 1
import os, re, requests, sys
tok = re.sub(r"\s+", "", os.environ["TOKEN"])
if not re.fullmatch(r"\d{6,}:[A-Za-z0-9_-]{30,}", tok):
    sys.exit("That does not look like a bot token (format 123456789:ABC...). Copy the API Token from BotFather again.")
me = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=20).json()
if not me.get("ok"):
    sys.exit(f"Telegram rejected the token: {me.get('description')}")
print("Bot found: @" + me["result"]["username"])
upd = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=20).json().get("result", [])
chats = [u["message"]["chat"]["id"] for u in upd if "message" in u]
if not chats:
    sys.exit("No chat found. Open @" + me["result"]["username"] + " in Telegram, press Start, send 'hi', then run this again.")
open("/tmp/.spectre_tg", "w").write(f"{tok}\n{chats[-1]}\n")
PY
TOK=$(sed -n 1p /tmp/.spectre_tg); CHAT=$(sed -n 2p /tmp/.spectre_tg); rm -f /tmp/.spectre_tg
for f in "${FILES[@]}"; do
  /usr/bin/grep -v '^TELEGRAM_' "$f" > "$f.tmp" 2>/dev/null
  { cat "$f.tmp"; echo "TELEGRAM_BOT_TOKEN=$TOK"; echo "TELEGRAM_CHAT_ID=$CHAT"; } > "$f"; rm -f "$f.tmp"; chmod 600 "$f"; echo "Saved to $f"
done
/usr/bin/curl -s "https://api.telegram.org/bot$TOK/sendMessage" -d chat_id="$CHAT" -d text="SPECTRE connected. Updates every 6 hours." >/dev/null && echo "Test message sent."
