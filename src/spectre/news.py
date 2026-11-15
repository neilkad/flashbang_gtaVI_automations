"""Fresh GTA 6 news -> Short plans. Headlines come from Google News RSS (free); the script uses only the headline,
the outlet name and (for stock) real quote data, framed as 'according to <outlet>'."""
from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "output"
SEEN = OUT / "news_seen.json"
PLANS = OUT / "news_plans"
FEEDS = (
    "https://news.google.com/rss/search?q=%22GTA+6%22+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=%22Grand+Theft+Auto+VI%22+OR+%22Rockstar+Games%22+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=%22Take-Two%22+GTA+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
)
RELEVANT = re.compile(r"gta\s*6|gta\s*vi|grand theft auto|rockstar|take-two|vice city|lucia", re.I)
BAD = re.compile(r"leak|rumou?r|reportedly cancel|nsfw|nude|sex|porn", re.I)
MODELS = ("gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash")


def _seen() -> set[str]:
    return set(json.loads(SEEN.read_text(encoding="utf-8"))) if SEEN.is_file() else set()


def _headlines() -> list[dict]:
    items = []
    for url in FEEDS:
        try:
            root = ET.fromstring(requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).content)
        except Exception:
            continue
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            source = (it.findtext("source") or "").strip()
            clean = re.sub(rf"\s+-\s+{re.escape(source)}$", "", title) if source else title
            try:
                age = (datetime.now(timezone.utc) - parsedate_to_datetime(it.findtext("pubDate"))).total_seconds() / 3600
            except Exception:
                age = 99
            if RELEVANT.search(clean) and not BAD.search(clean) and age <= 30:
                items.append({"headline": clean, "source": source, "link": it.findtext("link") or "", "age": age})
    items.sort(key=lambda i: i["age"])
    return items


def _stock_item() -> dict | None:
    try:
        meta = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/TTWO?range=5d&interval=1d",
                            headers={"User-Agent": "Mozilla/5.0"}, timeout=15).json()["chart"]["result"][0]["meta"]
        price, prev = meta["regularMarketPrice"], meta["chartPreviousClose"]
        change = (price - prev) / prev * 100
    except Exception:
        return None
    if abs(change) < 2:
        return None
    day = datetime.now().strftime("%Y-%m-%d")
    return {"headline": f"Take-Two Interactive (TTWO) stock is {change:+.1f}% at ${price:,.2f} versus the previous close",
            "source": "Yahoo Finance market data", "link": "https://finance.yahoo.com/quote/TTWO", "age": 0,
            "key": f"stock-{day}-{round(change)}", "stock": True}


def _ask(prompt: str) -> dict | None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=40_000))
    for attempt in range(len(MODELS) * 2):
        try:
            resp = client.models.generate_content(
                model=MODELS[attempt % len(MODELS)], contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"))
            data = json.loads(resp.text)
            if data.get("title") and data.get("voiceover") and len(data.get("beats", [])) == 3:
                return data
        except Exception as error:
            print(f"News plan retry {attempt + 1}: {str(error)[:100]}", flush=True)
            time.sleep(2)
    return None


def make_plan(slot: str, english: bool) -> bool:
    """Write output/news_plans/<slot>.json for the freshest unseen story. Returns False if nothing new."""
    seen = _seen()
    candidates = ([s] if (s := _stock_item()) else []) + _headlines()
    pick = next((c for c in candidates if (c.get("key") or c["headline"]) not in seen), None)
    if not pick:
        return False
    lang = ("pure English" if english else
            "natural Hinglish (Hindi written in Roman script mixed with simple English, like Indian gamers talk); write numbers and names as usual")
    prompt = (
        "You write a 35-second YouTube Short script about GTA 6 news. Use ONLY the facts in the headline below. "
        "Do not add details, numbers, quotes or causes that are not in it. Attribute it, e.g. 'According to "
        f"{pick['source']}', and never present rumours or leaks as confirmed. For stock stories only state the price move; "
        "never guess why it moved and never give investment advice. Tone: hyped, dramatic, curiosity-driven, fast-paced, like a top gaming Shorts creator; open with the hook, tease the reveal, end with a question that drives comments. No hate, no adult content.\n"
        f"Language: {lang}.\nHEADLINE: {pick['headline']}\nOUTLET: {pick['source']}\n\n"
        'Return ONLY JSON: {"title": "maximum-curiosity clickbait title under 70 chars (for example: WAIT... GTA 6 JUST DID THIS), 100% true to the headline, ending with one emoji", '
        '"thumbnail": "2-4 WORDS UPPERCASE", "hook": "shocking first sentence that stops the scroll in 2 seconds (a true teaser, never a false claim)", "voiceover": "70-95 words, ends with a question to the viewer", '
        '"beats": ["LABEL | DETAIL IN CAPS | visual", "LABEL | DETAIL IN CAPS | visual", "LABEL | DETAIL IN CAPS | visual"], '
        '"hashtags": ["#GTA6", "#GTAVI", "...up to 6 relevant"]}. Labels under 3 words; details under 8 words; no \'|\' inside text.'
    )
    data = _ask(prompt)
    if not data:
        return False
    PLANS.mkdir(parents=True, exist_ok=True)
    (PLANS / f"{slot}.json").write_text(json.dumps({**data, "lang": "en" if english else "hi", "source_link": pick["link"],
                                                    "source_name": pick["source"]}, indent=2), encoding="utf-8")
    SEEN.write_text(json.dumps(sorted(seen | {pick.get("key") or pick["headline"]})), encoding="utf-8")
    print(f"News plan for {slot}: {pick['headline'][:80]}", flush=True)
    return True


def load_plan(slot: str) -> dict | None:
    path = PLANS / f"{slot}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
