from pathlib import Path
import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_FILE = Path("client_secret.json")
TOKEN_FILE = Path("token.json")


def get_youtube():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES) if TOKEN_FILE.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CLIENT_FILE.exists():
            raise FileNotFoundError("Add your Google OAuth Desktop client JSON as client_secret.json first.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def authenticate():
    get_youtube()
    return TOKEN_FILE


def upload_video(video: str, title: str, description: str, tags: list[str], visibility: str = "private") -> str:
    if visibility not in {"private", "public", "unlisted"}:
        raise ValueError("visibility must be private, public, or unlisted")
    load_dotenv()
    video_path = Path(video).expanduser()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    youtube = get_youtube()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "tags": tags, "categoryId": "20"},
            "status": {
                "privacyStatus": visibility,
                "selfDeclaredMadeForKids": False,
                # Every scheduled SPECTRE Short uses AI narration and AI-assisted
                # original imagery, so disclose that use to YouTube as well as in
                # the viewer-facing description.
                "containsSyntheticMedia": True,
            },
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )
    response = request.execute()
    return response["id"]


def set_thumbnail(video_id: str, thumbnail: str) -> bool:
    """Best-effort custom thumbnail; returns False if YouTube rejects it (e.g. unverified channel)."""
    try:
        get_youtube().thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg")
        ).execute()
        return True
    except Exception as error:
        print(f"Thumbnail not set: {error}", flush=True)
        return False


def upload_private(video: str, title: str, description: str, tags: list[str]) -> str:
    """Backward-compatible private-upload helper."""
    return upload_video(video, title, description, tags, visibility="private")
