"""Pick the best moments from a livestream recording and cut them into vertical Shorts for review.

How moments are chosen (all local, no AI quota):
  1. ffmpeg's EBU R128 meter gives loudness every 0.1 s (shouts, explosions, crashes, gunfights are loud).
  2. ffmpeg scene detection gives visual-change spikes (chases, crashes, cuts).
  3. Each 5 s window is scored 0.6 * loudness peak + 0.4 * scene activity; the top windows that do not overlap are kept.
  4. Silent stretches and the first/last 30 s (setup and goodbye) are discarded.
Clips are written to the Review Queue folder as 'HL_<name>_<n>.mp4'. Delete the ones you dislike.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
REVIEW = Path.home() / "Documents" / "GTA VI" / "Review Queue" / "Stream Clips"
WINDOW = 5.0
CLIP_LEN = 40.0


def _loudness(video: Path) -> dict[int, float]:
    out = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    levels: dict[int, float] = {}
    for m in re.finditer(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+)", out):
        second = int(float(m.group(1)) // WINDOW)
        levels[second] = max(levels.get(second, -120.0), float(m.group(2)))
    return levels


def _scenes(video: Path) -> dict[int, int]:
    out = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf", "select='gt(scene,0.25)',metadata=print:file=-",
                          "-f", "null", "-"], capture_output=True, text=True).stdout
    counts: dict[int, int] = {}
    for m in re.finditer(r"pts_time:([\d.]+)", out):
        counts[int(float(m.group(1)) // WINDOW)] = counts.get(int(float(m.group(1)) // WINDOW), 0) + 1
    return counts


def pick_moments(video: Path, count: int = 8) -> list[float]:
    loud, scenes = _loudness(video), _scenes(video)
    if not loud:
        raise RuntimeError("No audio found in the recording.")
    peak_scenes = max(scenes.values(), default=1)
    ranked = []
    for idx, level in loud.items():
        start = idx * WINDOW
        if start < 30 or level < -40:  # skip intro and near-silence
            continue
        score = 0.6 * (level + 70) / 70 + 0.4 * scenes.get(idx, 0) / peak_scenes
        ranked.append((score, start))
    ranked.sort(reverse=True)
    chosen: list[float] = []
    for _, start in ranked:
        if all(abs(start - c) >= CLIP_LEN for c in chosen):
            chosen.append(start)
        if len(chosen) == count:
            break
    return sorted(chosen)


def cut(video: Path, start: float, dest: Path) -> None:
    begin = max(start - 12, 0)  # lead-in so the viewer sees what led to the peak
    vf = ("split[a][b];[a]scale=1080:1920,boxblur=30:5[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,"
          "format=yuv420p")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{begin:.1f}", "-t", str(CLIP_LEN), "-i", str(video), "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", str(dest)], check=True)


def run(recording: str, count: int = 8) -> list[Path]:
    video = Path(recording).expanduser()
    REVIEW.mkdir(parents=True, exist_ok=True)
    moments = pick_moments(video, count)
    out = []
    for n, start in enumerate(moments, 1):
        dest = REVIEW / f"HL_{video.stem[:20]}_{n:02d}_{int(start)}s.mp4"
        cut(video, start, dest)
        out.append(dest)
        print(f"Clip {n}: {int(start)}s -> {dest.name}", flush=True)
    return out
