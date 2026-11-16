"""Review-first queue: keep Shorts rendered ahead of time and publish one per hour."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .daily import _bank, _section, run_daily

REVIEW_DIR = Path.home() / "Documents" / "GTA VI" / "Review Queue"
QUEUE_FILE = Path("output/queue.json")
TARGET_AHEAD = 4
SLOT_MINUTES = 60
FIRST_HOUR = datetime(2026, 11, 15, 16)
LAST_HOUR = datetime(2026, 11, 18, 23)


@contextlib.contextmanager
def _qlock():
    """Serialise read-modify-write of queue.json between the publisher and the renderer."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE.parent / ".queue.lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


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
    with _qlock():
        return _add_rendered(slot, day, video, script)


def _add_rendered(slot: str, day: date, video: Path, script: Path) -> dict:
    data = _load()
    seq = data["next_seq"]
    data["next_seq"] = seq + 1
    title = re.sub(r"[^A-Za-z0-9 ]+", "", _section(script.read_text(encoding="utf-8"), "Title")).strip()[:60]
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    target = REVIEW_DIR / f"{seq + 1:03d}_{title}.mp4"
    target.write_bytes(Path(video).read_bytes())
    item = {"seq": seq, "slot": slot, "day": day.isoformat(), "file": str(target)}
    try:
        from . import news
        plan = news.load_plan(slot)
        if plan and plan.get("not_before"):
            item["not_before"] = plan["not_before"]
    except Exception:
        pass
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


YT_SLOTS = (15, 21)         # two YouTube Shorts a day
SOCIAL_SLOTS = (15, 21)     # the 15:00 and 21:00 Shorts also go to Instagram and Facebook as Reels
POSTING_START = datetime(2026, 11, 18)   # posting paused until Wednesday
CATCHUP_HOURS = 3           # a missed slot is still published for up to 3 hours


def _due_slot(now: datetime) -> tuple[str, int] | None:
    for hour in sorted(YT_SLOTS, reverse=True):
        start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if start <= now < start + timedelta(hours=CATCHUP_HOURS):
            return start.strftime("%Y-%m-%dT%H"), hour
    return None


def _notify(title: str, result: dict, social: bool) -> None:
    from . import report

    st = {}
    try:
        st = json.loads(Path(result["state"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        pass
    soc = st.get("social", {})
    lines = ["NEW POST LIVE", title, f"YouTube: {result.get('youtube_url', '-')}"]
    if social:
        lines.append(f"Facebook: {soc.get('facebook') or soc.get('facebook_error') or '-'}")
        lines.append(f"Instagram: {soc.get('instagram') or soc.get('instagram_error') or '-'}")
    report.alert("\n".join(lines))


def publish_next() -> str | None:
    """Publish the oldest reviewed Short when a daily slot is due and not yet used."""
    now = datetime.now()
    slot = _due_slot(now)
    if not slot or not (POSTING_START <= now <= LAST_HOUR + timedelta(hours=1)):
        return None
    key, hour = slot
    data = _load()
    if key in data.get("done_slots", []):
        return None
    now_iso = now.strftime("%Y-%m-%dT%H:%M")
    eligible = [i for i in _pending(data) if not i.get("not_before") or i["not_before"] <= now_iso]
    eligible.sort(key=lambda i: (0 if i.get("not_before") else 1, i["seq"]))  # campaign videos go first on their day
    if not eligible:
        return None
    item = eligible[0]
    social = hour in SOCIAL_SLOTS
    os.environ["SPECTRE_CROSSPOST"] = "1" if social else "0"
    result = run_daily(item["slot"], upload=True, day=date.fromisoformat(item["day"]), visibility="public")
    with _qlock():
        data = _load()
        for entry in data["items"]:
            if entry["seq"] == item["seq"]:
                entry["published"] = result.get("youtube_url", "")
        data.setdefault("done_slots", []).append(key)
        _save(data)
    Path(item["file"]).unlink(missing_ok=True)
    try:
        title = json.loads(Path(result["state"]).read_text(encoding="utf-8")).get("title", "")
        _notify(title, result, social)
    except Exception as error:
        print(f"Notify failed: {error}", flush=True)
    return result.get("youtube_url")


def tick() -> None:
    try:
        from . import streamshorts
        streamshorts.tick()
    except Exception as error:
        print(f"Stream shorts skipped: {error}", flush=True)
    try:
        url = publish_next()
        if url:
            print(f"Published {url}", flush=True)
    except Exception as error:
        print(f"Publish failed, will retry next tick: {error}", flush=True)


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
