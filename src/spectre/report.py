"""Six-hourly progress report, sent to WhatsApp through the free CallMeBot gateway (if configured)."""
from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "output"


def _stock() -> str:
    try:
        meta = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/TTWO?range=5d&interval=1d",
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=15).json()["chart"]["result"][0]["meta"]
        price, prev = meta["regularMarketPrice"], meta["chartPreviousClose"]
        change = (price - prev) / prev * 100
        return f"Take-Two (TTWO): ${price:,.2f} ({change:+.1f}% vs previous close)"
    except Exception:
        return "Take-Two (TTWO): price unavailable"


FULL_FORM = os.getenv("SPECTRE_FULL_FORM", "SPECTRE (Streaming, Previews, Edits, Comparisons, Trailers, Reactions & Explainers)")


def build() -> str:
    now = datetime.now()
    rows = []
    for path in sorted((OUT / "daily").glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    live = [r for r in rows if r.get("youtube_video_id")]
    recent = live[-3:]
    queue = {}
    try:
        queue = json.loads((OUT / "queue.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    waiting = [i for i in queue.get("items", []) if not i.get("published") and Path(i["file"]).is_file()]
    errors = [f"{r['slot']}: {r['social'].get(p + '_error')}" for r in live[-6:] for p in ("facebook", "instagram")
              if r.get("social", {}).get(p + "_error")]
    hours_left = max(int((datetime(2026, 11, 19) - now).total_seconds() // 3600), 0)
    lines = [f"{FULL_FORM} update {now:%d %b %H:%M}", f"{hours_left}h to GTA 6 launch",
             f"Published on YouTube: {len(live)} total", f"Queued ahead: {len(waiting)}"]
    lines += [f"- {r.get('title', '')[:60]} {r.get('youtube_url', '')}" for r in recent]
    lines.append(_stock())
    if errors:
        lines.append("Needs attention: " + "; ".join(errors[:3]))
    return "\n".join(lines)


def send() -> None:
    text = build()
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "reports" / f"update-{datetime.now():%Y%m%d-%H%M}.txt").write_text(text, encoding="utf-8")
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text, "disable_web_page_preview": "true"}, timeout=30)
        print("Telegram:", r.status_code)
        return
    phone, key = os.getenv("WHATSAPP_PHONE"), os.getenv("CALLMEBOT_APIKEY")
    if not (phone and key):
        print("No messaging app configured; report saved only.\n" + text)
        return
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode({"phone": phone, "text": text, "apikey": key})
    print("WhatsApp:", requests.get(url, timeout=30).status_code)


if __name__ == "__main__":
    send()
