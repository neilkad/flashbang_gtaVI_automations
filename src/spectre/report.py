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
    from . import dashboard

    st = dashboard.state()
    an = st["analytics"]
    P, F = an["platforms"], an["followers"]
    n = lambda x: "-" if x is None else f"{x:,}"
    views = sum(P[p]["views"] or 0 for p in P)
    likes = sum(P[p]["likes"] for p in P)
    comments = sum(P[p]["comments"] for p in P)
    last24 = {p: sum(h[p] for h in an["hours"]) for p in P}
    lines = [f"{FULL_FORM} update {datetime.now():%d %b %H:%M}", f"{st['countdown_hours']}h to GTA 6 launch", "",
             f"TOTAL: {an['all_posts']} posts | {n(views)} views | {n(likes)} likes | {n(comments)} comments",
             f"Followers: YT {n(F.get('youtube'))} | FB {n(F.get('facebook'))} | IG {n(F.get('instagram'))}", "",
             "BY PLATFORM (posts / views / likes / comments / last 24h)"]
    for key, label in (("youtube", "YouTube"), ("facebook", "Facebook"), ("instagram", "Instagram")):
        p = P[key]
        lines.append(f"{label}: {p['posts']} / {n(p['views'])} / {p['likes']} / {p['comments']} / {last24[key]}")
    lines += ["", f"Queue ahead: {len(st['queue'])} | Next slot: {st['next_slot']} | Scheduler: {st['agent']}", "", "TOP POSTS"]
    for r in an["top"][:5]:
        lines.append(f"- [{r['platform'][:2].upper()}] {(r.get('title') or '')[:55]} | {n(r.get('views'))} views, {r.get('likes') or 0} likes | {r.get('url')}")
    lines += ["", _stock()]
    if an["notes"]:
        lines.append("Note: " + "; ".join(an["notes"])[:200])
    return "\n".join(lines)[:4000]


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
