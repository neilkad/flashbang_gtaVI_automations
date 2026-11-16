"""Daily Shorts from your own livestream: detect new recordings, cut highlights for review, publish 1-2 a day."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from . import highlights, meta
from .youtube import upload_video

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
REC = ROOT / "input" / "stream-recordings"
STATE = ROOT / "output" / "stream_state.json"
START = datetime(2026, 11, 19)
SLOTS = (15, 21)           # up to two stream Shorts a day
CLIPS_PER_STREAM = 6
TITLES = (
    "I Did NOT Expect This In GTA 6 😱", "GTA 6 Live: This Went Wrong FAST 💀", "Watch Till The End... GTA 6 Chaos 🔥",
    "GTA 6 Fumble Of The Day 🤦", "Never Do This In GTA 6 😬", "GTA 6 Moment I Can't Believe Happened 🤯",
    "Chaos In Vice City 🌴💥", "I Almost Pulled It Off... GTA 6 😭", "GTA 6 Gameplay Gone Wrong 😂", "This Is Why I Fumble 🎮💀",
)
TAGS = ["#GTA6", "#GTAVI", "#GTA6Gameplay", "#GTA6Live", "#GamingShorts", "#Shorts", "#PS5", "#ViceCity", "#GamingFails", "#Funny"]
DISCLOSURE = ("Gameplay recorded live by Flashbang Fumbles. Grand Theft Auto VI (c) Rockstar Games / Take-Two Interactive. "
              "Unofficial fan channel, not affiliated with or endorsed by Rockstar Games or Take-Two.")


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {"processed": [], "posted": [], "n": 0}


def _save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cut_new_recordings() -> None:
    data = _state()
    for video in sorted(REC.glob("*.mp4")) + sorted(REC.glob("*.mkv")) + sorted(REC.glob("*.mov")):
        stat = video.stat()
        key = f"{video.name}:{stat.st_size}"
        # skip files still being written
        if key in data["processed"] or datetime.now().timestamp() - stat.st_mtime < 300:
            continue
        print(f"Cutting highlights from {video.name}", flush=True)
        highlights.run(str(video), CLIPS_PER_STREAM)
        data["processed"].append(key)
        _save(data)


def publish_due() -> None:
    now = datetime.now()
    if now < START or now.hour not in SLOTS:
        return
    data = _state()
    key = now.strftime("%Y-%m-%dT%H")
    if key in data["posted"]:
        return
    clips = sorted(highlights.REVIEW.glob("HL_*.mp4"))  # anything you delete in Finder is skipped
    if not clips:
        return
    clip = clips[0]
    n = data["n"]
    title = TITLES[n % len(TITLES)]
    description = f"{title}\n\n{DISCLOSURE}\n\nSubscribe: https://www.youtube.com/@flashbangfumbles\n\n{' '.join(TAGS)}"
    data["posted"].append(key)
    data["n"] = n + 1
    _save(data)
    try:
        vid = upload_video(str(clip), title, description, [t.lstrip("#") for t in TAGS], visibility="public")
    except Exception as error:
        data["posted"].remove(key)
        data["n"] = n
        _save(data)
        print(f"Stream Short upload failed: {error}", flush=True)
        return
    url = f"https://youtu.be/{vid}"
    social = {}
    try:
        social = meta.cross_post(clip, title, TAGS, DISCLOSURE)
    except Exception as error:
        social = {"error": str(error)[:200]}
    done = highlights.REVIEW / "posted"
    done.mkdir(exist_ok=True)
    clip.rename(done / clip.name)
    try:
        from . import report

        report.alert("NEW STREAM SHORT LIVE\n" + title + f"\nYouTube: {url}\nFacebook: {social.get('facebook') or social.get('facebook_error') or '-'}\n"
                     f"Instagram: {social.get('instagram') or social.get('instagram_error') or '-'}")
    except Exception:
        pass
    print(f"Stream Short posted: {url}", flush=True)


def tick() -> None:
    try:
        cut_new_recordings()
    except Exception as error:
        print(f"Stream cutting failed: {error}", flush=True)
    publish_due()
