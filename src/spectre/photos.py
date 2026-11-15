"""Five Instagram photo posts a day: stills from the official GTA VI footage cuts with fact-only captions."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from . import meta

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "output"
STATE = OUT / "photos.json"
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FONT = os.getenv("SPECTRE_FONT", "/System/Library/Fonts/Supplemental/Impact.ttf")
CORE = "#GTA6 #GTAVI #GrandTheftAutoVI #Rockstar #RockstarGames".split()
POOL = ("#GTA6Trailer #GTA6Release #GTA6Countdown #ViceCity #Leonida #LuciaAndJason #PS5 #XboxSeriesX #OpenWorld "
        "#GamingCommunity #Gamer #GamerLife #IndianGamers #GamingIndia #Hinglish #InstaGaming #VideoGames #NewGame "
        "#Explore #Trending #GTA6News #GTA6Gameplay #GamingMemes #ConsoleGaming #GamersOfInstagram #NewRelease").split()


def _tags(n: int) -> str:
    """Core tags plus a rotating slice of the pool, so posts are not identical."""
    start = (n * 7) % len(POOL)
    rotated = POOL[start:] + POOL[:start]
    return " ".join(CORE + rotated[:20])
DISCLOSURE = "AI disclosure: This post, its caption and graphics are AI-generated. Unofficial fan channel, not affiliated with Rockstar Games or Take-Two Interactive. Image from Rockstar Games' official GTA VI media (c) Rockstar Games / Take-Two."


def _lines(hours_left: int) -> list[tuple[str, str]]:
    return [
        (f"{hours_left} HOURS TO GO", f"Only {hours_left} hours left for GTA 6. Release: November 19, 2026 on PS5 and Xbox Series X|S. Are you ready?"),
        ("19 NOVEMBER 2026", "GTA 6 lands on November 19, 2026. Save this post and tag the friend you're playing with on day one."),
        ("VICE CITY IS BACK", "Vice City and the state of Leonida are the setting for GTA 6. Which area do you want to explore first?"),
        ("LUCIA AND JASON", "GTA 6 follows two leads, Lucia and Jason. Who are you playing as first?"),
        ("PS5 OR XBOX?", "GTA 6 is coming to PS5 and Xbox Series X|S. Where will you play? Comment below."),
        ("WHICH SCENE?", "Official GTA 6 footage from Rockstar. Rate this scene out of 10."),
        ("MIDNIGHT LAUNCH", "Rockstar says GTA 6 releases at midnight local time on November 19. Who is staying up?"),
        ("PRELOAD READY?", "Digital preload is open for pre-order holders. Clear your storage now so launch night goes smoothly."),
        ("TAG YOUR SQUAD", "Tag the friend who will not sleep on launch night. They know who they are."),
        ("SAVE THIS POST", f"{hours_left} hours to go. Save this post and come back on launch day to see how you felt."),
        ("DAY ONE PLAN", "What is the first thing you will do in GTA 6? Drive, explore or cause chaos? Tell us below."),
        ("RATE THE VIBES", "Neon, heat and Vice City energy. Rate the vibes of this scene from 1 to 10."),
        ("FIRST CAR?", "You can only pick one thing first in GTA 6: a fast car, a boat or a plane. What is it?"),
        ("WHO'S READY?", "Comment READY if you are counting the hours to GTA 6."),
    ]


def _frames() -> list[Path]:
    return sorted((ROOT / "input" / "photo-frames").glob("f*.jpg"))


def _make(frame: Path, text: str, dest: Path) -> None:
    safe = text.replace(":", "\\:").replace("'", "")
    vf = (f"drawbox=y=ih-300:w=iw:h=300:color=black@0.45:t=fill,"
          f"drawtext=fontfile='{FONT}':text='{safe}':fontsize=96:fontcolor=white:borderw=7:bordercolor=black:x=(w-text_w)/2:y=h-230,"
          f"drawtext=fontfile='{FONT}':text='GTA 6  •  @flashbangfumbles':fontsize=40:fontcolor=0xffe600:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-110")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(frame), "-vf", vf, "-update", "1", str(dest)], check=True)


def tick() -> None:
    now = datetime.now()
    if not (datetime(2026, 11, 15, 19) <= now <= datetime(2026, 11, 18, 23, 59)):
        return
    window = 1 if 15 <= now.minute < 30 else 2 if now.minute >= 45 else 0
    if not window:
        return
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {"done": [], "n": 0}
    key = now.strftime("%Y-%m-%dT%H") + f"p{window}"
    if key in state["done"] or not meta.enabled().get("instagram"):
        return
    clips = _frames()
    if not clips:
        return
    n = state["n"]
    hours_left = max(int((datetime(2026, 11, 19) - now).total_seconds() // 3600), 0)
    headline, body = _lines(hours_left)[n % len(_lines(hours_left))]
    dest = OUT / "photos" / f"{key.replace(':', '')}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _make(clips[n % len(clips)], headline, dest)
    caption = f"{body}\n\n{DISCLOSURE}\n\n{_tags(n)}"
    state["done"].append(key)
    state["n"] = n + 1
    try:
        state.setdefault("posts", []).append(meta.post_instagram_photo(dest, caption))
        print(f"Photo posted: {state['posts'][-1]}", flush=True)
    except Exception as error:
        state["done"].remove(key)
        state["n"] = n
        print(f"Photo post failed: {error}", flush=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
