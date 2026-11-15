# Moving hourly publishing to GitHub Actions (prepared, not enabled)

Status: the Mac launchd scheduler is the live publisher. This folder is the ready-to-go plan.

## Secrets to add (private repo → Settings → Secrets → Actions)
- `YOUTUBE_TOKEN_JSON` — contents of `token.json`
- `GOOGLE_CLIENT_SECRET_JSON` — contents of `client_secret.json`
- `GEMINI_API_KEY`

## Gaps to close at switch time
1. No local review folder on the runner; review = delete entries in `output/queue.json` in the repo (queue items point at absolute Mac paths, so the queue must be re-seeded on the runner).
2. The workflow sets `TZ: Asia/Kolkata` so the 16:00 Nov 15 – 23:00 Nov 18 window matches IST.
3. Rendered MP4s (~20 MB each) get committed; keep only ~4 ahead.
4. Commit only the ~10 MB footage cuts in `input/source-footage`, never `input-cache/`.
5. Stop the Mac scheduler first (`launchctl bootout gui/$(id -u)/com.spectre.gaming.scheduled-publish`) to avoid double posts.
6. The font is configurable via `SPECTRE_FONT` (already supported).
