"""Local live dashboard: serves one page and pushes state over a WebSocket."""
from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import serve
from websockets.http11 import Response

from .stats import get_channel, get_stats

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "output"
PORT = int(os.getenv("SPECTRE_DASHBOARD_PORT", "8765"))
LAUNCH = datetime(2026, 11, 19, 0, 0)
FIRST_SLOT = datetime(2026, 11, 15, 16)
LAST_SLOT = datetime(2026, 11, 18, 23)
TOKEN = secrets.token_urlsafe(16)
QUEUE = OUT / "queue.json"
LOCK = OUT / ".publish.lock"
REVIEW = Path.home() / "Documents" / "GTA VI" / "Review Queue"
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.spectre.gaming.scheduled-publish.plist"
JOB: dict = {"label": "", "started": "", "result": ""}


def _records() -> list[dict]:
    rows = []
    for path in sorted((OUT / "daily").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        data["_mtime"] = datetime.fromtimestamp(path.stat().st_mtime).strftime("%H:%M")
        data["_ts"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes")
        rows.append(data)
    return rows


def _log_tail(lines: int = 25, name: str = "scheduled-publish.log") -> list[str]:
    log = OUT / "logs" / name
    try:
        return log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def _agent_state() -> str:
    try:
        out = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/com.spectre.gaming.scheduled-publish"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return "running" if "state = running" in out else "loaded" if "state =" in out else "not loaded"


def _next_slot(now: datetime) -> str:
    base = now.replace(minute=0, second=0, microsecond=0)
    slot = base + timedelta(minutes=30) if now.minute < 30 else base + timedelta(hours=1)
    slot = max(slot, FIRST_SLOT)
    return slot.strftime("%Y-%m-%d %H:%M") if slot <= LAST_SLOT + timedelta(minutes=30) else "all slots done"


def _read_queue() -> dict:
    try:
        return json.loads(QUEUE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"next_seq": 0, "items": [], "last_published_hour": ""}


def _write_queue(data: dict) -> None:
    tmp = QUEUE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(QUEUE)


def _item_state(item: dict) -> dict:
    path = OUT / "daily" / f"{item['day']}-{item['slot']}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _script_path(item: dict) -> Path | None:
    rel = _item_state(item).get("script_path")
    return (ROOT / rel) if rel else None


def _section(md: str, heading: str) -> str:
    m = re.search(rf"^##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", md, flags=re.M | re.S | re.I)
    return m.group(1).strip() if m else ""


def _set_section(md: str, heading: str, text: str) -> str:
    return re.sub(
        rf"(^##\s+{re.escape(heading)}[^\n]*\n).*?(?=^##\s|\Z)",
        lambda m: m.group(1) + text.strip() + "\n\n",
        md, count=1, flags=re.M | re.S | re.I,
    )


def _pending() -> list[dict]:
    items = [i for i in _read_queue()["items"] if not i.get("published") and Path(i["file"]).is_file()]
    return sorted(items, key=lambda i: i["seq"])


def _queue_view() -> list[dict]:
    first = _next_slot(datetime.now())
    base = datetime.strptime(first, "%Y-%m-%d %H:%M") if first[0].isdigit() else None
    rows = []
    for n, item in enumerate(_pending()):
        script = _script_path(item)
        md = script.read_text(encoding="utf-8") if script and script.is_file() else ""
        desc = _section(md, "Description")
        rows.append({
            "seq": item["seq"], "slot": item["slot"], "file": Path(item["file"]).name,
            "title": _section(md, "Title"), "voiceover": _section(md, "Voiceover"),
            "beats": _section(md, "Visual beats"), "hook": _section(md, "Hook"),
            "description": desc.split("\n\nAI disclosure")[0].strip(),
            "hashtags": _section(md, "Hashtags"), "sources": _section(md, "Sources"),
            "mb": round(Path(item["file"]).stat().st_size / 1e6, 1),
            "goes_live": (base + timedelta(minutes=30 * n)).strftime("%a %d %b %H:%M") if base and base + timedelta(minutes=30 * n) <= LAST_SLOT + timedelta(minutes=30) else "after launch window",
        })
    return rows


def _busy() -> bool:
    return LOCK.exists()


def _run_job(label: str, args: list[str]) -> str:
    if JOB.get("label") and _busy():
        return f"Busy: {JOB['label']}"
    try:
        LOCK.mkdir()
    except FileExistsError:
        return "Busy: the scheduler or another job is running"
    JOB.update(label=label, started=datetime.now().strftime("%H:%M:%S"), result="running")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "SPECTRE_ROOT": str(ROOT), "SPECTRE_AUDIO_MODE": "narrated"}
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip().removeprefix("export ").strip(), v.strip().strip("'\""))

    def work() -> None:
        try:
            log = (OUT / "logs" / "dashboard-jobs.log").open("a", encoding="utf-8")
            log.write(f"\n== {datetime.now():%F %T} {label}\n"); log.flush()
            code = subprocess.run([sys.executable, "-m", "spectre.cli", *args], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
            JOB["result"] = "done" if code == 0 else f"failed (exit {code})"
        finally:
            shutil.rmtree(LOCK, ignore_errors=True)

    threading.Thread(target=work, daemon=True).start()
    return f"Started: {label}"


def _launchctl(verb: str) -> str:
    uid = os.getuid()
    loaded = _agent_state() != "not loaded"
    if verb == "resume" and loaded:
        return "Scheduler is already running — nothing to resume"
    if verb == "pause" and not loaded:
        return "Scheduler is already paused"
    cmd = ["launchctl", "bootout", f"gui/{uid}/com.spectre.gaming.scheduled-publish"] if verb == "pause" else ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        return f"{verb} failed: {out.stderr.strip() or out.stdout.strip()}"
    return "Scheduler paused — no uploads until you resume" if verb == "pause" else "Scheduler resumed"


def action(name: str, q: dict) -> str:
    arg = lambda k: q.get(k, [""])[0]
    seq = int(arg("seq")) if arg("seq").lstrip("-").isdigit() else None
    data = _read_queue()
    if name == "pause":
        return _launchctl("pause")
    if name == "resume":
        return _launchctl("resume")
    if name == "publish_now":
        return _run_job(f"Publishing #{seq} now", ["queue-publish", "--seq", str(seq)])
    if name == "tick_now":
        return _run_job("Hourly tick", ["queue-tick"])
    if name == "refill":
        return _run_job("Refilling queue", ["queue-refill"])
    if name == "rerender":
        return _run_job(f"Re-rendering #{seq}", ["queue-rerender", "--seq", str(seq)])
    if name == "set_target":
        data["target"] = max(1, min(12, int(arg("n") or 4)))
        _write_queue(data)
        return f"Queue size set to {data['target']}"
    if name == "toggle_social":
        platform = arg("platform")
        if platform not in {"facebook", "instagram"}:
            return "Unknown platform"
        path = OUT / "social_flags.json"
        flags = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        flags[platform] = not flags.get(platform, True)
        path.write_text(json.dumps(flags), encoding="utf-8")
        return f"{platform.title()} posting " + ("ON" if flags[platform] else "OFF")
    if name == "toggle_refill":
        data["paused_refill"] = not data.get("paused_refill")
        _write_queue(data)
        return "Auto-refill " + ("paused" if data["paused_refill"] else "on")
    if name == "remove":
        item = next((i for i in data["items"] if i["seq"] == seq), None)
        if item:
            Path(item["file"]).unlink(missing_ok=True)
            item["rejected"] = True
            _write_queue(data)
        return f"Removed #{seq}"
    if name == "move":
        order = _pending()
        idx = next((n for n, i in enumerate(order) if i["seq"] == seq), None)
        other = idx + (-1 if arg("dir") == "up" else 1) if idx is not None else None
        if other is None or not 0 <= other < len(order):
            return "Can't move further"
        a, b = order[idx], order[other]
        by = {i["seq"]: i for i in data["items"]}
        by[a["seq"]]["seq"], by[b["seq"]]["seq"] = b["seq"], a["seq"]
        _write_queue(data)
        return "Moved"
    if name in {"set_title", "set_desc", "set_tags", "set_voiceover"}:
        item = next((i for i in data["items"] if i["seq"] == seq and not i.get("published")), None)
        script = _script_path(item) if item else None
        if not script or not script.is_file():
            return "Script not found"
        text = arg("text").strip()
        if not text:
            return "Empty text ignored"
        heading = {"set_title": "Title", "set_desc": "Description", "set_tags": "Hashtags", "set_voiceover": "Voiceover"}[name]
        md = script.read_text(encoding="utf-8")
        if name == "set_desc":
            tail = _section(md, "Description")
            text = text + ("\n\n" + tail[tail.index("AI disclosure"):] if "AI disclosure" in tail else "")
        script.write_text(_set_section(md, heading, text.replace("\n", " ") if name == "set_title" else text), encoding="utf-8")
        if name == "set_voiceover":
            return "Voiceover saved. Press Re-render to apply it to the video."
        return f"{heading} saved"
    if name == "open_folder":
        subprocess.run(["open", str(REVIEW)])
        return "Opened Review Queue folder"
    return "Unknown action"


def _analytics(stats: dict, published: list[dict]) -> dict:
    from . import meta

    social = meta.fetch_stats()
    yt = [{"id": r["youtube_video_id"], "url": r.get("youtube_url"), "title": r.get("title"), "time": r.get("_ts"),
           **{k: stats.get(r["youtube_video_id"], {}).get(k) for k in ("views", "likes", "comments", "shares")}} for r in published]

    def local_hour(iso: str | None) -> str | None:
        if not iso:
            return None
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00").replace("+0000", "+00:00"))
            return (dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt).strftime("%Y-%m-%dT%H")
        except ValueError:
            return None

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = [(now - timedelta(hours=h)).strftime("%Y-%m-%dT%H") for h in range(23, -1, -1)]
    per_hour = {h: {"youtube": 0, "facebook": 0, "instagram": 0} for h in hours}
    for name, rows in (("youtube", yt), ("facebook", social["facebook"]), ("instagram", social["instagram"])):
        for r in rows:
            h = local_hour(r.get("time"))
            if h in per_hour:
                per_hour[h][name] += 1

    def totals(rows: list[dict]) -> dict:
        views = [r.get("views") for r in rows if r.get("views") is not None]
        return {"posts": len(rows), "views": sum(views) if views else None, "likes": sum(r.get("likes") or 0 for r in rows),
                "comments": sum(r.get("comments") or 0 for r in rows), "shares": sum(r.get("shares") or 0 for r in rows)}

    platforms = {"youtube": totals(yt), "facebook": totals(social["facebook"]), "instagram": totals(social["instagram"])}
    for name, rows in (("youtube", yt), ("facebook", social["facebook"]), ("instagram", social["instagram"])):
        for r in rows:
            r["platform"] = name
    everything = [*yt, *social["facebook"], *social["instagram"]]
    everything.sort(key=lambda r: (r.get("views") or 0) + 5 * (r.get("likes") or 0) + 10 * (r.get("comments") or 0), reverse=True)
    channel = get_channel()
    return {"platforms": platforms, "hours": [{"h": h[-2:] + ":00", **per_hour[h]} for h in hours], "top": everything[:12],
            "followers": {"youtube": channel.get("subs"), **social.get("followers", {})}, "notes": social.get("notes", []),
            "channel": channel, "all_posts": sum(p["posts"] for p in platforms.values())}


def _social() -> dict:
    flags = {}
    try:
        flags = json.loads((OUT / "social_flags.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    meta = ROOT / "meta_state.json"
    try:
        info = json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}
    except ValueError:
        info = {}
    return {"connected": bool(info.get("page_id")), "ig": info.get("ig_username", ""), "page": info.get("page_name", ""),
            "facebook": flags.get("facebook", True), "instagram": flags.get("instagram", True)}


def _published_detail() -> list[dict]:
    rows = []
    for r in reversed([r for r in _records() if r.get("youtube_video_id")]):
        video = ROOT / r["video_path"] if r.get("video_path") else None
        script = ROOT / r["script_path"] if r.get("script_path") else None
        md = script.read_text(encoding="utf-8") if script and script.is_file() else ""
        rows.append({
            "id": r["youtube_video_id"], "url": r.get("youtube_url"), "title": r.get("title"), "date": r.get("date"),
            "slot": r.get("slot"), "time": r.get("_mtime"), "local": bool(video and video.is_file()),
            "voiceover": _section(md, "Voiceover"), "description": r.get("description", ""), "tags": r.get("tags", []),
            "privacy": r.get("privacy"), "social": r.get("social", {}),
        })
    return rows


def build_report(day: str) -> str:
    rows = [r for r in _records() if r.get("date") == day]
    done = [r for r in rows if r.get("youtube_video_id")]
    lines = [f"# SPECTRE daily report — {day}", "", f"Published: {len(done)} / {len(rows)} attempted", ""]
    for r in done:
        lines.append(f"- {r['slot']}: {r['title']} — {r.get('youtube_url', '')}")
    failed = [r for r in rows if not r.get("youtube_video_id")]
    if failed:
        lines += ["", "Not yet published: " + ", ".join(r["slot"] for r in failed)]
    return "\n".join(lines) + "\n"


def state() -> dict:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    rows = _records()
    published = [r for r in rows if r.get("youtube_video_id")]
    days: dict[str, int] = {}
    for r in published:
        days[r["date"]] = days.get(r["date"], 0) + 1
    stats = get_stats([r["youtube_video_id"] for r in published])
    totals = {k: sum(v.get(k, 0) for v in stats["data"].values()) for k in ("views", "likes", "comments", "shares", "subs_gained")}
    return {
        "stats_error": stats["error"],
        "stats_note": stats["note"],
        "totals": totals,
        "stats": stats["data"],
        "now": now.strftime("%H:%M:%S"),
        "countdown_hours": max(int((LAUNCH - now).total_seconds() // 3600), 0),
        "agent": _agent_state(),
        "next_slot": _next_slot(now),
        "today_count": days.get(today, 0),
        "total": len(published),
        "per_day": days,
        "videos": [
            {k: r.get(k) for k in ("date", "slot", "title", "youtube_url", "youtube_video_id", "_mtime")}
            for r in reversed(published[-30:])
        ],
        "log": _log_tail(),
        "queue": _queue_view(),
        "queue_target": _read_queue().get("target", 4),
        "refill_paused": bool(_read_queue().get("paused_refill")),
        "busy": _busy(),
        "job": JOB,
        "job_log": _log_tail(12, "dashboard-jobs.log"),
        "library": _published_detail(),
        "social": _social(),
        "analytics": _analytics(stats["data"], published),
        "window_end": LAST_SLOT.strftime("%d %b %H:%M"),
    }


def _write_report() -> None:
    day = datetime.now().strftime("%Y-%m-%d")
    path = OUT / "reports" / f"{day}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_report(day), encoding="utf-8")


PAGE = (Path(__file__).parent / "dashboard.html")


def _media(path: str, q: dict) -> Response | None:
    file = None
    if q.get("seq"):
        item = next((i for i in _pending() if str(i["seq"]) == q["seq"][0]), None)
        file = Path(item["file"]) if item else None
    elif q.get("id"):
        rec = next((r for r in _records() if r.get("youtube_video_id") == q["id"][0]), None)
        file = ROOT / rec["video_path"] if rec and rec.get("video_path") else None
    if not file or not file.is_file():
        return Response(404, "Not Found", _headers("text/plain"), b"missing")
    return Response(200, "OK", _headers("video/mp4"), file.read_bytes())


def _remote_pass() -> str:
    path = OUT / "remote_pass.txt"
    if not path.is_file():
        path.write_text(secrets.token_urlsafe(18), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def _is_local(host: str) -> bool:
    return host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")


def _cookie_ok(request) -> bool:
    return f"spk={_remote_pass()}" in request.headers.get("Cookie", "")


async def _http(connection, request):
    url = urlparse(request.path)
    q = parse_qs(url.query)
    host = request.headers.get("Host", "")
    local = _is_local(host) and "Cf-Ray" not in request.headers and "Cf-Connecting-Ip" not in request.headers
    # Remote (phone/tunnel) access is view-only and needs the private link's passcode.
    if not local and not (_cookie_ok(request) or q.get("k", [""])[0] == _remote_pass()):
        return Response(403, "Forbidden", _headers("text/plain"), b"forbidden")
    if url.path == "/ws":
        return None
    if url.path.startswith("/api/") or url.path == "/media":
        if not local or q.get("t", [""])[0] != TOKEN:
            return Response(403, "Forbidden", _headers("text/plain"), b"forbidden")
        if url.path == "/media":
            return _media(url.path, q)
        try:
            msg = await asyncio.get_running_loop().run_in_executor(None, action, url.path[5:], q)
        except Exception as error:  # surface to the UI instead of dropping the socket
            msg = f"Error: {error}"
        return Response(200, "OK", _headers("application/json"), json.dumps({"msg": msg}).encode())
    if url.path == "/report":
        body = build_report(datetime.now().strftime("%Y-%m-%d")).encode()
        return Response(200, "OK", _headers("text/plain; charset=utf-8"), body)
    body = PAGE.read_bytes().replace(b"__TOKEN__", TOKEN.encode() if local else b"")
    headers = _headers("text/html; charset=utf-8")
    if not local:
        headers["Set-Cookie"] = f"spk={_remote_pass()}; Path=/; Max-Age=2592000; Secure; HttpOnly; SameSite=Lax"
    return Response(HTTPStatus.OK.value, "OK", headers, body)


def _headers(content_type: str):
    from websockets.datastructures import Headers

    return Headers([("Content-Type", content_type), ("Cache-Control", "no-store")])


async def _handler(ws):
    while True:
        await ws.send(json.dumps(state()))
        await asyncio.sleep(2)


async def _reporter():
    while True:
        _write_report()
        await asyncio.sleep(600)


async def main() -> None:
    _remote_pass()
    asyncio.create_task(_reporter())
    async with serve(_handler, "127.0.0.1", PORT, process_request=_http):
        print(f"SPECTRE dashboard: http://127.0.0.1:{PORT}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
