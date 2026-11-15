# SPECTRE Gaming Agent

A local Mac workflow for generating and rendering gaming Shorts, then uploading them to YouTube as **private** drafts. You review and publish each draft yourself.

## What it does

- Generates a concise, voiceover-ready Short about gaming news, GTA VI theories, countdowns, or gaming facts.
- Renders a vertical 1080×1920 MP4 with expressive Gemini narration, timed scene cards based on the script's visual beats, and on-screen captions.
- Saves the script, video, title, description, hashtags, and processing state under `output/`.
- Uploads a finished video file to YouTube with `privacyStatus=private` by default.
- Leaves public publishing to you.

The intended pre-launch schedule has two slots in India time: an official-facts countdown at noon and a clearly labeled theory at 6 PM. The `daily` command runs one slot at a time; recurring automation is not enabled until FFmpeg and YouTube OAuth are configured. The pre-launch plan ends November 18, 2026. Rockstar currently lists the game for November 19, 2026, on PlayStation 5 and Xbox Series X|S. After launch, stream clips require local recordings from your livestream; this project does not yet select highlights automatically.

## 1. Install

Requires Python 3.10 or later. macOS may provide an older `python3`. Install Python 3.13 from the [official Python macOS downloads](https://www.python.org/downloads/macos/) first. Open a new Terminal window, go to this folder, and use `python3.13` explicitly:

```bash
python3.13 -m venv .venv313
source .venv313/bin/activate
python -m pip install -e .
cp .env.example .env
```

Edit `.env` and add your Gemini API key. Keep `.env` private; it is excluded from version control.
For daily video rendering, install Homebrew's full FFmpeg build once with `brew install ffmpeg-full`. Narration uses Gemini TTS (default voice: Puck, an upbeat conversational voice) through the Gemini API key in `.env`. The default voice and delivery style can be changed with `SPECTRE_TTS_VOICE`, `SPECTRE_TTS_MODEL`, and `SPECTRE_TTS_STYLE`.

## 2. Generate a Short script or daily video

```bash
spectre generate --topic "Three GTA VI details fans may have missed" --category gta-theory
```

The script is saved under `output/scripts/`. Categories: `gaming-news`, `gta-theory`, `countdown`, `gaming-fact`, `entertaining-short`.

Create one of the two pre-launch videos without uploading it:

```bash
spectre daily --slot noon --no-upload
spectre daily --slot evening --no-upload
```

Each daily run uses Gemini Flash-Lite for the script, Gemini TTS for narration, and FFmpeg for the 9:16 MP4. It saves the video under `output/videos/`. For time-sensitive news, verify every claim and source before publishing.

## 3. Connect YouTube (one-time setup)

1. In Google Cloud Console, create/select a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen for your account and create an **OAuth Client ID** of type **Desktop app**.
3. Download its JSON file and save it as `client_secret.json` in this project folder. Do not share or commit it.
4. In the activated virtual environment, run:

```bash
spectre youtube-auth
```

Your browser opens for Google sign-in and consent. The resulting `token.json` stays local and is ignored by Git.

## 4. Upload a finished video privately

```bash
spectre upload \
  --video /path/to/finished-short.mp4 \
  --title "Your reviewed title" \
  --description "Description and sources" \
  --tags "GTA VI,gaming,shorts"
```

The default visibility is private. To make the command require an explicit confirmation flag, set `REQUIRE_UPLOAD_CONFIRMATION=true` in `.env` and then include `--confirm-upload`. The uploader refuses public or unlisted uploads; change visibility manually in YouTube Studio after reviewing the private draft.

Once YouTube authorization is configured, run one daily slot with its default private upload:

```bash
spectre daily --slot noon
spectre daily --slot evening
```

The daily command is idempotent for each date and slot: rerunning it reuses the saved video and does not upload a second copy if the first upload succeeded.

## Project layout

```text
src/spectre/       CLI, Gemini generation, video rendering, and YouTube API helpers
output/scripts/    Generated Markdown scripts
output/videos/     Rendered vertical MP4 videos
output/daily/      Per-date/per-slot state to avoid duplicate uploads
client_secret.json Google OAuth desktop client (you provide this)
token.json         Local OAuth token (created on first authentication)
```

## Privacy and reliability notes

- Never put API keys, OAuth files, or tokens in a shared folder or public repository.
- Gemini output can be wrong or stale. Verify news, dates, rumors, and claims; label theories as speculation.
- The renderer turns each visual beat into a timed branded graphic card. It does not fetch or include GTA footage; add only footage you have rights to use. Check each generated card and caption before uploading.
- Daily automation depends on the Mac being available, internet access, a valid Gemini key, FFmpeg, and YouTube OAuth authorization.
- YouTube uploads may take time to process. Confirm the draft appears in YouTube Studio before relying on it.
- The upload script sets `selfDeclaredMadeForKids` to false. Review the audience setting and all other video details in Studio.
- YouTube API quotas and Google OAuth verification requirements are controlled by Google and may change.
