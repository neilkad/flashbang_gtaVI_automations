"""Read-only YouTube stats. Uses a separate token so uploads keep working untouched."""
from __future__ import annotations

from pathlib import Path
import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(os.getenv("SPECTRE_ROOT", Path(__file__).resolve().parents[2]))
TOKEN = ROOT / "token_read.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
_cache: dict = {"at": 0.0, "data": {}, "error": None}


def authorize() -> None:
    flow = InstalledAppFlow.from_client_secrets_file(str(ROOT / "client_secret.json"), SCOPES)
    TOKEN.write_text(flow.run_local_server(port=0).to_json(), encoding="utf-8")
    print("Saved", TOKEN)


def _creds():
    if not TOKEN.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _fetch(ids: list[str]) -> dict:
    creds = _creds()
    if creds is None:
        raise PermissionError("not connected")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    data: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        for item in yt.videos().list(part="statistics,status,contentDetails", id=",".join(ids[i:i + 50])).execute().get("items", []):
            st = item.get("statistics", {})
            data[item["id"]] = {
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "privacy": item.get("status", {}).get("privacyStatus"),
                "uploadStatus": item.get("status", {}).get("uploadStatus"),
            }
    try:
        an = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        rows = an.reports().query(
            ids="channel==MINE", startDate="2026-11-01", endDate=time.strftime("%Y-%m-%d"),
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,shares,subscribersGained,subscribersLost",
            dimensions="video", filters="video==" + ",".join(ids[:500]),
        ).execute().get("rows", [])
        for r in rows:
            if r[0] in data:
                data[r[0]].update(
                    minutes=r[2], avg_duration=r[3], avg_pct=round(r[4], 1),
                    shares=r[6], subs_gained=r[7], subs_lost=r[8],
                )
    except Exception as exc:
        _cache["note"] = f"Analytics API: {str(exc)[:90]}"
    return data


def get_stats(ids: list[str]) -> dict:
    """Cached for 60 s so the 2 s dashboard push never hammers the API."""
    if time.time() - _cache["at"] > 60 and ids:
        try:
            _cache.update(data=_fetch(ids), error=None)
        except Exception as exc:
            _cache["error"] = "not connected" if isinstance(exc, PermissionError) else str(exc)[:120]
        _cache["at"] = time.time()
    return {"data": _cache["data"], "error": _cache["error"], "note": _cache.get("note")}


if __name__ == "__main__":
    authorize()
