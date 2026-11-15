"""Review-first queue: keep Shorts rendered ahead of time and publish one per hour."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from .daily import _bank, _section, run_daily

REVIEW_DIR = Path.home() / "Documents" / "GTA VI" / "Review Queue"
QUEUE_FILE = Path("output/queue.json")
TARGET_AHEAD = 6
SLOT_MINUTES = 30
FIRST_HOUR = datetime(2026, 11, 15, 16)
LAST_HOUR = datetime(2026, 11, 18, 23)


def _load() -> dict:
    if QUEUE_FILE.is_file():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {"next_seq": 0, "items": [], "last_published_hour": ""}


def _save(data: dict) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def plan_for_slot(day: date, slot: str):
    """Topic for a queue slot named q<seq>: rotate through the topic bank."""
    bank = _bank(day)
    return bank[int(slot[1:]) % len(bank)]


def _pending(data: dict) -> list[dict]:
    live = []
    for item in data["items"]:
        if item.get("published"):
            continue
        if not Path(item["file"]).is_file():
            continue  # the user removed it from the review folder = rejected
        live.append(item)
    return sorted(live, key=lambda i: i["seq"])


def add_rendered(slot: str, day: date, video: Path, script: Path) -> dict:
    data = _load()
    seq = data["next_seq"]
    data["next_seq"] = seq + 1
    title = re.sub(r"[^A-Za-z0-9 ]+", "", _section(script.read_text(encoding="utf-8"), "Title")).strip()[:60]
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    target = REVIEW_DIR / f"{seq + 1:03d}_{title}.mp4"
    target.write_bytes(Path(video).read_bytes())
    item = {"seq": seq, "slot": slot, "day": day.isoformat(), "file": str(target)}
    data["items"].append(item)
    _save(data)
    return item


def refill(target: int | None = None) -> None:
    """Render until the review folder holds `target` unpublished Shorts."""
    while True:
        target = target or int(_load().get("target", TARGET_AHEAD))
        data = _load()
        if _load().get("paused_refill"):
            return
        if len(_pending(data)) >= target:
            return
        seq = data["next_seq"]
        day = datetime.now().date()
        slot = f"q{seq:03d}"
        os.environ["SPECTRE_FOOTAGE_OFFSET"] = str(seq)
        try:
            from . import news
            from .daily import _is_english_slot
            news.make_plan(slot, english=_is_english_slot(slot))
        except Exception as error:
            print(f"News plan skipped: {error}", flush=True)
        result = run_daily(slot, upload=False, day=day, visibility="private")
        add_rendered(slot, day, Path(result["video"]), Path(result["script"]))
        print(f"Queued {slot}", flush=True)


def publish_next() -> str | None:
    """Publish the oldest reviewed Short if this hour has not had one yet."""
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%dT%H") + ("a" if now.minute < SLOT_MINUTES else "b")
    if not (FIRST_HOUR <= now.replace(minute=0, second=0, microsecond=0) <= LAST_HOUR):
        return None
    data = _load()
    if data.get("last_published_hour") == hour_key:
        return None
    pending = _pending(data)
    if not pending:
        refill(1)
        data = _load()
        pending = _pending(data)
    item = pending[0]
    result = run_daily(item["slot"], upload=True, day=date.fromisoformat(item["day"]), visibility="public")
    data = _load()
    for entry in data["items"]:
        if entry["seq"] == item["seq"]:
            entry["published"] = result.get("youtube_url", "")
    data["last_published_hour"] = hour_key
    _save(data)
    Path(item["file"]).unlink(missing_ok=True)
    return result.get("youtube_url")


def tick() -> None:
    url = publish_next()
    if url:
        print(f"Published {url}", flush=True)
    try:
        from . import photos
        photos.tick()
    except Exception as error:
        print(f"Photos skipped: {error}", flush=True)
    try:
        from . import report
        report.watchdog()
    except Exception as error:
        print(f"Watchdog skipped: {error}", flush=True)
    refill()


def publish_item(seq: int | None = None) -> str | None:
    """Publish a queued Short right now (default: the oldest), outside the hourly cadence."""
    data = _load()
    pending = _pending(data)
    item = next((i for i in pending if seq is None or i["seq"] == seq), None)
    if not item:
        return None
    result = run_daily(item["slot"], upload=True, day=date.fromisoformat(item["day"]), visibility="public")
    data = _load()
    for entry in data["items"]:
        if entry["seq"] == item["seq"]:
            entry["published"] = result.get("youtube_url", "")
    _save(data)
    Path(item["file"]).unlink(missing_ok=True)
    return result.get("youtube_url")


def rerender(seq: int) -> None:
    """Throw away the rendered video for a queued item and render it again."""
    data = _load()
    item = next((i for i in data["items"] if i["seq"] == seq and not i.get("published")), None)
    if not item:
        return
    state_file = Path("output/daily") / f"{item['day']}-{item['slot']}.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    Path(state.get("video_path", "")).unlink(missing_ok=True)
    state.pop("video_path", None)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.environ["SPECTRE_FOOTAGE_OFFSET"] = str(seq + 3)
    result = run_daily(item["slot"], upload=False, day=date.fromisoformat(item["day"]), visibility="private")
    Path(item["file"]).write_bytes(Path(result["video"]).read_bytes())
    print(f"Re-rendered {item['slot']}", flush=True)
