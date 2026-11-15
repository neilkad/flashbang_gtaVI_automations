# Livestream recordings -> highlight Shorts

After each stream, save the recording here (OBS local recording, or download your own stream's VOD from YouTube Studio), then run:

    .venv313/bin/python -m spectre.cli highlights --recording "input/stream-recordings/<file>.mp4" --count 8

It picks the loudest, most action-heavy 5-second windows (shouts, crashes, gunfights, chases), skips the first 30 s and silent parts, and cuts 40 s vertical clips (blurred-background 9:16) into `~/Documents/GTA VI/Review Queue/` as `HL_*.mp4`. Delete the ones you dislike.

Never put OAuth files or API keys here.
