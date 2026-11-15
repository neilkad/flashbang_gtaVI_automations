"""Cross-post finished Shorts to a Facebook Page and an Instagram account via the Meta Graph API."""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import requests

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
STATE = ROOT / "meta_state.json"
API = "https://graph.facebook.com/v21.0"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload/v21.0"


class MetaError(RuntimeError):
    pass


def _call(method: str, url: str, **kw) -> dict:
    resp = requests.request(method, url, timeout=kw.pop("timeout", 120), **kw)
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:300]}
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", data)
        raise MetaError(f"{err.get('message', err)} (code {err.get('code', resp.status_code)})")
    return data


def _load() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {}


def _save(data: dict) -> None:
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    STATE.chmod(0o600)


def setup() -> dict:
    """Exchange the pasted token for a long-lived one and discover the Page and Instagram IDs."""
    app, secret, token = (os.environ[k] for k in ("META_APP_ID", "META_APP_SECRET", "META_USER_TOKEN"))
    long = _call("GET", f"{API}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app, "client_secret": secret, "fb_exchange_token": token})
    user_token = long["access_token"]
    pages = _call("GET", f"{API}/me/accounts", params={
        "fields": "name,id,access_token,instagram_business_account{id,username}", "access_token": user_token})["data"]
    if not pages:
        raise MetaError("No Facebook Page found for this token. Re-generate it and select your Page when asked.")
    page = pages[0]
    ig = page.get("instagram_business_account") or {}
    state = {
        "user_token": user_token, "page_id": page["id"], "page_name": page["name"], "page_token": page["access_token"],
        "ig_id": ig.get("id"), "ig_username": ig.get("username"),
        "expires_in": long.get("expires_in"), "saved_at": int(time.time()),
    }
    _save(state)
    return {k: v for k, v in state.items() if "token" not in k}


def enabled() -> dict:
    state = _load()
    flags = _load_flags()
    return {"facebook": bool(state.get("page_id")) and flags.get("facebook", True),
            "instagram": bool(state.get("ig_id")) and flags.get("instagram", True)}


def _load_flags() -> dict:
    path = ROOT / "output" / "social_flags.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def post_facebook(video: Path, caption: str) -> str:
    state = _load()
    page, token = state["page_id"], state["page_token"]
    size = Path(video).stat().st_size
    start = _call("POST", f"{API}/{page}/video_reels", data={"upload_phase": "start", "access_token": token})
    vid = start["video_id"]
    with open(video, "rb") as handle:
        _call("POST", start["upload_url"], timeout=600, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}, data=handle)
    _call("POST", f"{API}/{page}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": caption, "access_token": token})
    return f"https://www.facebook.com/reel/{vid}"


@contextlib.contextmanager
def _public_url(video: Path):
    """Serve one file through a temporary free Cloudflare quick tunnel and yield its public URL."""
    cf = Path(os.getenv("CLOUDFLARED", Path.home() / ".spectre-bin" / "cloudflared"))
    if not cf.is_file():
        raise MetaError("cloudflared is missing (expected at ~/.spectre-bin/cloudflared)")
    serve_dir = Path(tempfile.mkdtemp(prefix="spectre-share-"))
    name = f"{int(time.time())}{Path(video).suffix}"
    shutil.copy(video, serve_dir / name)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            pass

    handler = functools.partial(Quiet, directory=str(serve_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    proc = subprocess.Popen([str(cf), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{server.server_port}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    url = None
    deadline = time.time() + 45
    try:
        while time.time() < deadline and url is None:
            line = proc.stderr.readline()
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line or "")
            if match:
                url = match.group(0)
            elif proc.poll() is not None:
                break
        if not url:
            raise MetaError("Could not open a temporary public link for Instagram")
        for _ in range(20):
            try:
                if requests.head(f"{url}/{name}", timeout=10).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        yield f"{url}/{name}"
    finally:
        proc.terminate()
        server.shutdown()
        shutil.rmtree(serve_dir, ignore_errors=True)


def post_instagram(video: Path, caption: str) -> str:
    _ig_guard(94)
    state = _load()
    ig, token = state["ig_id"], state["page_token"]
    with _public_url(Path(video)) as link:
        container = _call("POST", f"{API}/{ig}/media", data={
            "media_type": "REELS", "video_url": link, "caption": caption, "access_token": token})
        for _ in range(60):
            status = _call("GET", f"{API}/{container['id']}", params={"fields": "status_code,status", "access_token": token})
            if status.get("status_code") == "FINISHED":
                break
            if status.get("status_code") == "ERROR":
                raise MetaError(f"Instagram could not process the video: {status.get('status')}")
            time.sleep(5)
        else:
            raise MetaError("Instagram processing timed out")
    published = _call("POST", f"{API}/{ig}/media_publish", data={"creation_id": container["id"], "access_token": token})
    info = _call("GET", f"{API}/{published['id']}", params={"fields": "permalink", "access_token": token})
    return info.get("permalink", "")


_EXTRA_TAGS = ("#GTA6Release", "#GTA6Countdown", "#GTA6Gameplay", "#GTA6Trailer", "#GrandTheftAutoVI", "#RockstarGames",
               "#OpenWorld", "#PS5Games", "#XboxGames", "#GamingCommunity", "#GamerLife", "#IndianGamers", "#GamingIndia",
               "#Reels", "#ReelsIndia", "#ViralReels", "#ExplorePage", "#FYP", "#Hinglish", "#GamingReels")


def _tags(hashtags: list[str], limit: int) -> str:
    seen: list[str] = []
    for tag in [*hashtags, *_EXTRA_TAGS]:
        if tag.lower() not in {t.lower() for t in seen}:
            seen.append(tag)
    return " ".join(seen[:limit])


_stats_cache: dict = {"at": 0.0, "data": {}}


def fetch_stats() -> dict:
    """Instagram and Facebook post numbers (cached 5 min). Views need extra Meta permissions; likes/comments don't."""
    if time.time() - _stats_cache["at"] < 300:
        return _stats_cache["data"]
    state = _load()
    out: dict = {"instagram": [], "facebook": [], "followers": {}, "notes": []}
    if not state.get("page_id"):
        return out
    token = state["page_token"]
    try:
        media = _call("GET", f"{API}/{state['ig_id']}/media", params={
            "fields": "id,media_type,permalink,like_count,comments_count,timestamp,caption", "limit": 100, "access_token": token}, timeout=40)["data"]
        for m in media:
            row = {"id": m["id"], "type": m.get("media_type"), "url": m.get("permalink"), "likes": m.get("like_count", 0),
                   "comments": m.get("comments_count", 0), "time": m.get("timestamp"), "title": (m.get("caption") or "")[:70]}
            try:
                ins = _call("GET", f"{API}/{m['id']}/insights", params={
                    "metric": "views,reach,shares,saved", "access_token": token}, timeout=30)["data"]
                for item in ins:
                    row[item["name"]] = item["values"][0]["value"]
            except MetaError:
                out["notes"].append("instagram_insights") if "instagram_insights" not in out["notes"] else None
            out["instagram"].append(row)
        prof = _call("GET", f"{API}/{state['ig_id']}", params={"fields": "followers_count,media_count", "access_token": token}, timeout=30)
        out["followers"]["instagram"] = prof.get("followers_count", 0)
    except Exception as error:
        out["notes"].append(f"instagram: {str(error)[:80]}")
    try:
        reels = _call("GET", f"{API}/{state['page_id']}/video_reels", params={
            "fields": "id,description,created_time,permalink_url,likes.summary(true),comments.summary(true),views",
            "limit": 100, "access_token": token}, timeout=40)["data"]
        for r in reels:
            out["facebook"].append({"id": r["id"], "url": r.get("permalink_url") or f"https://www.facebook.com/reel/{r['id']}",
                                    "likes": r.get("likes", {}).get("summary", {}).get("total_count", 0),
                                    "comments": r.get("comments", {}).get("summary", {}).get("total_count", 0),
                                    "views": r.get("views"), "time": r.get("created_time"), "title": (r.get("description") or "")[:70]})
        page = _call("GET", f"{API}/{state['page_id']}", params={"fields": "followers_count,fan_count", "access_token": token}, timeout=30)
        out["followers"]["facebook"] = page.get("followers_count", page.get("fan_count", 0))
    except Exception as error:
        out["notes"].append(f"facebook: {str(error)[:80]}")
    _stats_cache.update(at=time.time(), data=out)
    return out


def _ig_guard(limit: int) -> None:
    """Refuse to publish when Instagram's rolling 24h quota usage is at or above `limit` (of 100)."""
    state = _load()
    try:
        data = _call("GET", f"{API}/{state['ig_id']}/content_publishing_limit",
                     params={"fields": "quota_usage", "access_token": state["page_token"]}, timeout=30)["data"][0]
        used = int(data.get("quota_usage", 0))
    except Exception:
        return  # if the check itself fails, let the real publish call decide
    if used >= limit:
        raise MetaError(f"Instagram daily quota guard: {used}/100 used in 24h (limit {limit}); skipped to stay safe")


def post_instagram_photo(image: Path, caption: str) -> str:
    _ig_guard(80)
    state = _load()
    ig, token = state["ig_id"], state["page_token"]
    with _public_url(Path(image)) as link:
        container = _call("POST", f"{API}/{ig}/media", data={"image_url": link, "caption": caption, "access_token": token})
        for _ in range(30):
            status = _call("GET", f"{API}/{container['id']}", params={"fields": "status_code,status", "access_token": token})
            if status.get("status_code") == "FINISHED":
                break
            if status.get("status_code") == "ERROR":
                raise MetaError(f"Instagram could not process the photo: {status.get('status')}")
            time.sleep(3)
    published = _call("POST", f"{API}/{ig}/media_publish", data={"creation_id": container["id"], "access_token": token})
    return _call("GET", f"{API}/{published['id']}", params={"fields": "permalink", "access_token": token}).get("permalink", "")


def cross_post(video: Path, title: str, hashtags: list[str], disclosure: str, skip: tuple = ()) -> dict:
    """Post to every enabled platform; one failure never blocks the others."""
    results: dict = {}
    flags = enabled()
    for name, fn, limit in (("facebook", post_facebook, 12), ("instagram", post_instagram, 25)):
        if not flags[name] or name in skip:
            continue
        caption = f"{title}\n\n{disclosure}\n\n{_tags(hashtags, limit)}"[:2100]
        try:
            results[name] = fn(Path(video), caption)
        except Exception as error:
            results[name + "_error"] = str(error)[:300]
    return results


if __name__ == "__main__":
    print(json.dumps(setup(), indent=2))
