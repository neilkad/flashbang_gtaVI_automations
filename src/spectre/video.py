"""Create a narrated, captioned vertical video from a SPECTRE Markdown script."""

from pathlib import Path
import os
import re
import shutil
import subprocess
import textwrap
import tempfile
import wave

from dotenv import load_dotenv
from google import genai
from google.genai import types


FONT = os.getenv("SPECTRE_FONT", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
THEME_ASSET_DIR = Path("assets/gta-theme")
SOURCE_ASSET_DIR = Path("assets/original-visuals")
FOOTAGE_DIR = Path("input/source-footage")


def _ffmpeg_tool(name: str) -> str | None:
    """Prefer Homebrew's full FFmpeg build, which includes text filters."""
    override = os.getenv(f"SPECTRE_{name.upper()}_BIN")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return str(candidate)
        raise RuntimeError(f"{name} was not found at SPECTRE_{name.upper()}_BIN={override}")

    for prefix in (Path("/opt/homebrew"), Path("/usr/local")):
        candidate = prefix / "opt" / "ffmpeg-full" / "bin" / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def _section(markdown: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _plain_text(value: str) -> str:
    value = re.sub(r"\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`", lambda m: next(x for x in m.groups() if x is not None), value)
    value = re.sub(r"\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"[\U00010000-\U0010ffff]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _caption_chunks(voiceover: str, words_per_caption: int = 7) -> list[str]:
    words = re.findall(r"\S+", _plain_text(voiceover))
    return [" ".join(words[index:index + words_per_caption]) for index in range(0, len(words), words_per_caption)]


def _visual_beats(markdown: str) -> list[tuple[str, str, str]]:
    """Read a short label, on-screen copy, and visual idea from each beat."""
    section = _section(markdown, "Visual beats")
    beats: list[tuple[str, str, str]] = []
    for line in section.splitlines():
        line = re.sub(r"^\s*(?:[-*+]\s*)?(?:\d+[.)]\s*)?", "", line)
        line = _plain_text(line).strip(" -—|:")
        if not line:
            continue
        parts = [part.strip(" .:-") for part in line.split("|")]
        label = parts[0]
        detail = parts[1] if len(parts) > 1 else ""
        visual = parts[2] if len(parts) > 2 else ""
        if len(parts) == 1:
            words = label.split()
            label, visual = " ".join(words[:5]), " ".join(words[5:])
        beats.append((label[:48], detail[:100], visual[:120]))
        if len(beats) == 6:
            break
    return beats


def _beat_highlight(label: str, detail: str, visual: str) -> str:
    text = f"{label} {detail} {visual}"
    date = re.search(r"\b(?:NOV(?:EMBER)?\s+\d{1,2}|DEC(?:EMBER)?\s+\d{1,2})\b", text, re.IGNORECASE)
    clock = re.search(r"\b(?:\d{1,2}(?::\d{2})?\s*(?:AM|PM)\s+GMT|MIDNIGHT(?:\s+LOCAL)?)\b", text, re.IGNORECASE)
    values = [match.group(0).upper().replace("  ", " ") for match in (date, clock) if match]
    if values:
        return "\n".join("\n".join(textwrap.wrap(value, width=9)) for value in values)
    if re.search(r"\b(?:REGION|SOURCE|CHECK)\b", text, re.IGNORECASE):
        return "CHECK\nYOUR\nREGION"
    return "\n".join(textwrap.wrap(label.upper(), width=12)[:3])


def _ass_timestamp(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    whole_seconds, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def _write_ass(chunks: list[str], duration: float, path: Path) -> None:
    weight = sum(max(1, len(chunk.split())) for chunk in chunks)
    cursor = 0.0
    entries = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&HAA000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,2,50,50,300,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for index, chunk in enumerate(chunks, 1):
        share = max(1, len(chunk.split())) / weight
        end = duration if index == len(chunks) else cursor + duration * share
        wrapped = r"\N".join(textwrap.wrap(chunk, width=24))
        entries.append(
            f"Dialogue: 0,{_ass_timestamp(cursor)},{_ass_timestamp(end)},Default,,0,0,0,,{wrapped}"
        )
        cursor = end
    path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def _audio_duration(ffprobe: str, path: Path) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _create_theme_background(ffmpeg: str, duration: float, temp_dir: Path) -> Path | None:
    """Build a vertical, cinematic background from original channel artwork."""
    images = sorted(
        path for path in THEME_ASSET_DIR.glob("*")
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not images:
        return None

    background_path = temp_dir / "theme-background.mp4"
    image_duration = duration / len(images)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for image in images:
        command.extend(["-loop", "1", "-framerate", "30", "-t", f"{image_duration:.3f}", "-i", str(image.resolve())])

    chains = []
    for index in range(len(images)):
        chains.append(
            f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,trim=duration={image_duration:.3f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[v{index}]"
        )
    if len(images) == 1:
        output_label = "[v0]"
    else:
        chains.append("".join(f"[v{index}]" for index in range(len(images))) + f"concat=n={len(images)}:v=1:a=0[bg]")
        output_label = "[bg]"
    command.extend([
        "-filter_complex", ";".join(chains),
        "-map", output_label,
        "-an",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        str(background_path),
    ])
    subprocess.run(command, cwd=temp_dir, check=True)
    return background_path


def _source_media_assets(prefer_featured: bool = True) -> list[Path]:
    """Return creator-approved visual assets in a stable order."""
    footage = sorted(FOOTAGE_DIR.glob("*.mp4")) if FOOTAGE_DIR.is_dir() else []
    # Per-game clips live in input/source-footage/gta1..gta5 (and rdr2); games named in the script go first.
    text = os.getenv("SPECTRE_FOOTAGE_TEXT", "").lower()
    games = {"gta1": ("gta 1", "gta1", "gta one"), "gta2": ("gta 2", "gta2"), "gta3": ("gta 3", "gta3"),
             "gta4": ("gta 4", "gta4", "gta iv"), "gta5": ("gta 5", "gta5", "gta v", "gta five"),
             "rdr2": ("rdr2", "red dead")}
    older = [clip for game, names in games.items() if any(n in text for n in names)
             for clip in sorted((FOOTAGE_DIR / game).glob("*.mp4"))]
    if older and os.getenv("SPECTRE_FOOTAGE", "1") != "0":
        return (older + footage)[:8]
    if footage and os.getenv("SPECTRE_FOOTAGE", "1") != "0":
        shift = int(os.getenv("SPECTRE_FOOTAGE_OFFSET", "0")) % len(footage)
        return (footage[shift:] + footage[:shift])[:8]
    if not SOURCE_ASSET_DIR.is_dir():
        return []
    allowed = {".mp4", ".mov", ".mkv", ".webm", ".png", ".jpg", ".jpeg", ".webp"}
    assets = sorted(path for path in SOURCE_ASSET_DIR.iterdir() if path.is_file() and path.suffix.lower() in allowed)
    # A file prefixed with 00_ is the featured approved source.  This lets a
    # trailer excerpt provide continuous official dialogue and music instead
    # of intercutting it with silent press clips.
    featured = [path for path in assets if path.name.startswith("00_")]
    regular = [path for path in assets if not path.name.startswith("00_")]
    if prefer_featured and featured:
        return featured
    return (regular or assets)[:8]


def _create_source_background(
    ffmpeg: str,
    duration: float,
    temp_dir: Path,
    audio_volume: float = 1.0,
    prefer_featured: bool = True,
) -> Path | None:
    """Build a dynamic vertical montage with the creator's approved clip audio."""
    assets = _source_media_assets(prefer_featured=prefer_featured)
    if not assets:
        return None

    output_path = temp_dir / "source-footage-background.mp4"
    piece = duration / len(assets)
    videos = {".mp4", ".mov", ".mkv", ".webm"}
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for asset in assets:
        if asset.suffix.lower() in videos:
            command.extend(["-stream_loop", "-1", "-t", f"{piece:.3f}", "-i", str(asset.resolve())])
        else:
            command.extend(["-loop", "1", "-framerate", "30", "-t", f"{piece:.3f}", "-i", str(asset.resolve())])

    chains = []
    audio_chains = []
    videos = {".mp4", ".mov", ".mkv", ".webm"}
    for index, asset in enumerate(assets):
        chains.append(
            f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,trim=duration={piece:.3f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[v{index}]"
        )
        if asset.suffix.lower() in videos:
            audio_chains.append(
                f"[{index}:a]atrim=duration={piece:.3f},asetpts=PTS-STARTPTS,volume={audio_volume:.2f}[a{index}]"
            )
        else:
            audio_chains.append(
                f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={piece:.3f}[a{index}]"
            )
    if len(assets) == 1:
        output_label = "[v0]"
        audio_label = "[a0]"
    else:
        chains.append("".join(f"[v{index}]" for index in range(len(assets))) + f"concat=n={len(assets)}:v=1:a=0[bg]")
        output_label = "[bg]"
        audio_chains.append("".join(f"[a{index}]" for index in range(len(assets))) + f"concat=n={len(assets)}:v=0:a=1[bga]")
        audio_label = "[bga]"
    command.extend([
        "-filter_complex", ";".join(chains + audio_chains),
        "-map", output_label,
        "-map", audio_label,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        str(output_path),
    ])
    subprocess.run(command, cwd=temp_dir, check=True)
    return output_path


def _cover_text(markdown: str, title: str) -> str:
    """Short, self-explanatory cover headline: the first beat's key detail, else the title."""
    beats = _visual_beats(markdown)
    source = beats[0][1] if beats else title
    words = re.sub(r"[^\w\s'?!%-]", "", source.upper()).split()[:5]
    return "\n".join(textwrap.wrap(" ".join(words), width=12))


def _create_music_bed(ffmpeg: str, duration: float, path: Path) -> None:
    """Synthesize an original high-energy music loop (no third-party audio)."""
    kick = "aevalsrc='0.9*sin(2*PI*(55+90*exp(-14*mod(t,0.5)))*mod(t,0.5))*exp(-7*mod(t,0.5))':s=44100"
    bass = "aevalsrc='0.35*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*2*t))+0.18*sin(2*PI*110*t)*lt(mod(t,1),0.5)':s=44100"
    lead = "aevalsrc='0.12*sin(2*PI*(220+110*floor(mod(t*4,4)))*t)*(0.5+0.5*sin(2*PI*8*t))':s=44100"
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", kick,
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", bass,
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", lead,
        "-filter_complex", "[0][1][2]amix=inputs=3:normalize=0,alimiter=limit=0.9,aformat=sample_rates=48000:channel_layouts=stereo[m]",
        "-map", "[m]", "-c:a", "pcm_s16le", str(path),
    ], check=True)


def _generate_narration(voiceover: str, output_path: Path, voice_name: str) -> None:
    """Generate expressive narration with Gemini TTS and save its WAV output."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file to generate natural narration.")

    model = os.getenv("SPECTRE_TTS_MODEL", "gemini-3.8-flash-tts").strip()
    # Keep the direction short: long style prompts get read aloud by the TTS model.
    style = os.getenv("SPECTRE_TTS_STYLE", "confidently, with punchy energy").strip()
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "180"))
    client = genai.Client(
        api_key=api_key,
        # Gemini TTS models are exposed on v1beta, even when text generation
        # on the same API key uses the stable v1 endpoint.
        http_options=types.HttpOptions(api_version="v1beta", timeout=timeout_seconds * 1000),
    )
    print(f"Generating natural narration with Gemini ({model}, {voice_name})...", flush=True)
    models = [model]
    for fallback in ("gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"):
        if fallback not in models:
            models.append(fallback)
    prompt = voiceover  # speak only the script; no direction text
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
    )
    for candidate in models:
        try:
            response = client.models.generate_content(model=candidate, contents=prompt, config=config)
            if candidate != model:
                print(f"Using available Gemini TTS model: {candidate}", flush=True)
            break
        except Exception as exc:
            message = str(exc).lower()
            unavailable = "not found" in message and "model" in message
            quota = any(k in message for k in ("429", "resource_exhausted", "500", "internal", "503"))
            if not (unavailable or quota):
                raise
            if candidate == models[-1]:
                raise RuntimeError(
                    "No configured Gemini TTS model is available to this API key. "
                    "Try gemini-3.1-flash-tts-preview or gemini-2.5-flash-preview-tts in .env."
                ) from exc
            print(f"{candidate} is unavailable for this key; trying the supported fallback...", flush=True)
    candidates = getattr(response, "candidates", None) or []
    audio_data = None
    for candidate_response in candidates:
        content = getattr(candidate_response, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                audio_data = inline_data.data
                break
        if audio_data:
            break
    if not audio_data:
        raise RuntimeError("Gemini TTS returned no audio. Try again or choose another supported voice.")
    if isinstance(audio_data, str):
        raise RuntimeError("Gemini TTS returned encoded audio where raw PCM was expected.")
    if not audio_data:
        raise RuntimeError("Gemini TTS returned an empty audio file.")
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(audio_data)


def _english_text(script_path: Path) -> None:
    """Hinglish scripts get English on-screen captions and beat text (cached in the script)."""
    markdown = script_path.read_text(encoding="utf-8")
    if "<!-- hinglish -->" not in markdown or "## English captions" in markdown and "<!-- en -->" in markdown:
        return
    beats = _section(markdown, "Visual beats")
    prompt = (
        "Translate this Hinglish YouTube Shorts script to natural, short English for on-screen captions. "
        "Keep every fact, number and name exactly. Return ONLY JSON: "
        '{"captions": "full English text of the voiceover", "beats": ["label | detail | visual", ...]} '
        "with the same number and order of beats; keep the visual field and any '//' separators unchanged, UPPERCASE the label and detail.\n\n"
        f"VOICEOVER:\n{_section(markdown, 'Voiceover')}\n\nBEATS:\n{beats}"
    )
    import json as _json
    import time as _time
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=40_000))
    data = None
    models = ("gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    for attempt in range(len(models) * 2):
        try:
            response = client.models.generate_content(
                model=models[attempt % len(models)], contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"))
            data = _json.loads(response.text)
            break
        except Exception as error:
            print(f"English caption translation retry {attempt + 1}: {str(error)[:120]}", flush=True)
            _time.sleep(2)
    captions = (data or {}).get("captions", "").strip()
    new_beats = (data or {}).get("beats") or []
    old_lines = [line for line in beats.splitlines() if line.strip()]
    if not captions:
        markdown = markdown.rstrip() + "\n\n## English captions\n<!-- en -->\n\n"
    else:
        markdown = markdown.rstrip() + f"\n\n## English captions\n<!-- en -->\n{captions}\n\n"
        if len(new_beats) == len(old_lines):
            markdown = re.sub(r"(^##\s+Visual beats[^\n]*\n).*?(?=^##\s)",
                              lambda m: m.group(1) + "\n".join(f"- {b.lstrip('- ').strip()}" for b in new_beats) + "\n\n",
                              markdown, count=1, flags=re.M | re.S)
    script_path.write_text(markdown, encoding="utf-8")


def create_video(script_path: str | Path, voice: str | None = None, require_source_media: bool = False) -> Path:
    """Render a branded 9:16 MP4 with Gemini narration and on-screen captions."""
    script_path = Path(script_path)
    if not script_path.is_file():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    os.environ["SPECTRE_FOOTAGE_TEXT"] = script_path.read_text(encoding="utf-8")

    ffmpeg = _ffmpeg_tool("ffmpeg")
    ffprobe = _ffmpeg_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Video rendering needs FFmpeg and ffprobe. Install Homebrew's full build with: brew install ffmpeg-full")
    filters = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    available_filters = {line.split()[1] for line in filters.splitlines() if len(line.split()) >= 2}
    required_filters = {"drawgrid", "drawbox", "drawtext", "subtitles"}
    missing_filters = sorted(required_filters - available_filters)
    if missing_filters:
        raise RuntimeError(
            "This FFmpeg build is missing required video filters: "
            f"{', '.join(missing_filters)}. Install Homebrew's full build with: brew install ffmpeg-full"
        )
    if not Path(FONT).is_file():
        raise RuntimeError(f"The caption font was not found: {FONT}")

    try:
        _english_text(script_path)
    except Exception as error:
        print(f"English captions skipped: {error}", flush=True)
    markdown = script_path.read_text(encoding="utf-8")
    title = _plain_text(_section(markdown, "Title"))
    voiceover = _plain_text(_section(markdown, "Voiceover"))
    if not title or not voiceover:
        raise ValueError("The script needs non-empty 'Title' and 'Voiceover' sections.")
    if require_source_media and not _source_media_assets():
        raise RuntimeError(
            "Public scheduled Shorts need approved footage or screenshots in input/source-footage. "
            "No video was uploaded."
        )

    output_dir = Path("output/videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{script_path.stem}.mp4"
    voice_name = voice or os.getenv("SPECTRE_TTS_VOICE", "Puck")
    # Existing .env files from the starter may still contain macOS's old default.
    if voice_name.strip().casefold() == "samantha":
        voice_name = "Puck"

    with tempfile.TemporaryDirectory(prefix="spectre-render-") as temp_name:
        temp_dir = Path(temp_name)
        audio_path = temp_dir / "voice.wav"
        (temp_dir / "title.txt").write_text("\n".join(textwrap.wrap(title, width=26)), encoding="utf-8")
        beats = _visual_beats(markdown)
        if not beats:
            beats = [(title, "Original, creator-led Short.", "SPECTRE GAMING graphic card")]
        for index, (label, detail, visual) in enumerate(beats):
            if " // " in detail:
                top, bottom = detail.split(" // ", 1)
                for key, value in (("top", top), ("bottom", bottom)):
                    (temp_dir / f"beat-{index}-{key}.txt").write_text(
                        "\n".join(textwrap.wrap(value.upper(), width=17)[:3]), encoding="utf-8"
                    )
            (temp_dir / f"beat-{index}-label.txt").write_text(
                "\n".join(textwrap.wrap(label.upper(), width=22)[:1]), encoding="utf-8"
            )
            (temp_dir / f"beat-{index}-detail.txt").write_text(
                "\n".join(textwrap.wrap(detail, width=28)[:2]), encoding="utf-8"
            )
            (temp_dir / f"beat-{index}-highlight.txt").write_text(
                _beat_highlight(label, detail, visual), encoding="utf-8"
            )
        # Narration is the default because trailer dialogue and music are protected
        # by YouTube's rights checks.  "official" is kept for private review only.
        audio_mode = os.getenv("SPECTRE_AUDIO_MODE", "narrated").strip().casefold()
        official_audio_only = False  # third-party audio is never used
        narration_available = not official_audio_only
        if narration_available:
            _generate_narration(voiceover, audio_path, voice_name)
            if not audio_path.is_file() or audio_path.stat().st_size == 0:
                raise RuntimeError("Gemini narration generation produced an empty audio file.")
            duration = _audio_duration(ffprobe, audio_path)
            if duration <= 0:
                raise RuntimeError("Gemini narration produced an empty audio track.")
        else:
            print("Using official GTA VI clip audio with on-screen captions.", flush=True)
            duration = 48.0

        captions_path = temp_dir / "captions.ass"
        english = _section(markdown, "English captions").replace("<!-- en -->", "").strip()
        hinglish = "<!-- hinglish -->" in markdown
        _write_ass(_caption_chunks(english if hinglish else voiceover) if (english or not hinglish) else [], duration, captions_path)
        source_background = _create_source_background(
            ffmpeg,
            duration,
            temp_dir,
            audio_volume=1.45 if official_audio_only else 1.0,
            prefer_featured=official_audio_only,
        )
        music_path = temp_dir / "music.wav"
        _create_music_bed(ffmpeg, duration, music_path)
        theme_background = source_background or _create_theme_background(ffmpeg, duration, temp_dir)
        graph = [
            "eq=brightness=-0.06:saturation=1.08",
            f"drawtext=fontfile='{FONT}':text='SPECTRE GAMING':fontcolor=0x57F3FA:fontsize=34:borderw=4:bordercolor=black:x=(w-text_w)/2:y=70",
            f"drawtext=fontfile='{FONT}':textfile=title.txt:fontcolor=white:fontsize=44:borderw=5:bordercolor=black:line_spacing=8:x=(w-text_w)/2:y=120",
            f"drawtext=fontfile='{FONT}':text='Footage\\: Rockstar Games official media':fontcolor=white@0.8:fontsize=24:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-150",
            f"drawtext=fontfile='{FONT}':text='FOLLOW @flashbangfumbles':fontcolor=0xffe600:fontsize=30:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-205",
        ]
        colors = ["0x36E5F0", "0xFF4D8D", "0xF7C948", "0x8E7CFF", "0x56E39F"]
        scene_duration = duration / len(beats)
        for index, _ in enumerate(beats):
            start = index * scene_duration
            end = duration if index == len(beats) - 1 else (index + 1) * scene_duration
            window = f"between(t,{start:.3f},{end:.3f})"
            color = colors[index % len(colors)]
            if " // " in beats[index][1] and beats[index][2].upper() == "MEME":
                graph.extend([
                    f"drawtext=fontfile='{FONT}':textfile=beat-{index}-top.txt:fontcolor=white:fontsize=92:borderw=9:bordercolor=black:line_spacing=14:x=(w-text_w)/2:y=330:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':textfile=beat-{index}-bottom.txt:fontcolor=white:fontsize=92:borderw=9:bordercolor=black:line_spacing=14:x=(w-text_w)/2:y=1150:enable='{window}'",
                ])
                continue
            if " // " in beats[index][1]:
                series = beats[index][2].upper() == "SERIES"
                versus = re.match(r"\s*(.+?)\s+vs\.?\s+(.+?)(?:\s*[:\-]|\s+(?:kaun|ka|kya)\b|$)", title, flags=re.IGNORECASE)
                left, right = (versus.group(1).upper(), versus.group(2).upper()) if versus else ("GTA V  ·  2013", "GTA VI  ·  2026")
                left, right = re.sub(r"[^A-Z0-9 ·.']", "", left)[:26], re.sub(r"[^A-Z0-9 ·.']", "", right)[:26]
                hdr_top = beats[index][0].upper() if series else left
                hdr_bottom = "WHAT CHANGED" if series else right
                badge = "NEW" if series else "VS"
                graph.extend([
                    f"drawbox=x=60:y=300:w=960:h=470:color=0x0A2A3A@0.5:t=fill:enable='{window}'",
                    f"drawbox=x=60:y=300:w=960:h=12:color=0x36E5F0@1:t=fill:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':text='{hdr_top}':fontcolor=0x36E5F0:fontsize=40:x=100:y=345:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':textfile=beat-{index}-top.txt:fontcolor=white:fontsize=72:line_spacing=16:x=100:y=450:enable='{window}'",
                    f"drawbox=x=60:y=830:w=960:h=470:color=0x3A0A24@0.5:t=fill:enable='{window}'",
                    f"drawbox=x=60:y=830:w=960:h=12:color=0xFF2E88@1:t=fill:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':text='{hdr_bottom}':fontcolor=0xFF2E88:fontsize=40:x=100:y=875:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':textfile=beat-{index}-bottom.txt:fontcolor=white:fontsize=72:line_spacing=16:x=100:y=980:enable='{window}'",
                    f"drawbox=x=440:y=748:w=200:h=104:color=0xFFE600@1:t=fill:enable='{window}'",
                    f"drawtext=fontfile='{FONT}':text='{badge}':fontcolor=black:fontsize=72:x=(w-text_w)/2:y=768:enable='{window}'",
                ])
                continue
            graph.extend([
                f"drawbox=x=60:y=1090:w=10:h=170:color={color}@1.0:t=fill:enable='{window}'",
                f"drawtext=fontfile='{FONT}':textfile=beat-{index}-label.txt:fontcolor={color}:fontsize=64:borderw=6:bordercolor=black:x=95:y=1085:enable='{window}'",
                f"drawtext=fontfile='{FONT}':textfile=beat-{index}-detail.txt:fontcolor=white:fontsize=44:borderw=5:bordercolor=black:line_spacing=10:x=95:y=1170:enable='{window}'",
            ])
        # Opening cover frame: YouTube uses an early frame as the Shorts cover.
        (temp_dir / "cover.txt").write_text(_cover_text(markdown, title), encoding="utf-8")
        graph.extend([
            "drawbox=x=0:y=0:w=iw:h=ih:color=0x07111F@0.55:t=fill:enable='lt(t,0.5)'",
            f"drawtext=fontfile='{FONT}':textfile=cover.txt:fontcolor=0xFFE600:fontsize=118:borderw=10:bordercolor=black:line_spacing=18:x=(w-text_w)/2:y=(h-text_h)/2:enable='lt(t,0.5)'",
        ])
        graph.append("subtitles=filename=captions.ass")
        filter_graph = ",".join(graph)
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        if theme_background:
            command.extend(["-i", str(theme_background)])
        else:
            command.extend(["-f", "lavfi", "-i", f"color=c=0x07111F:s=1080x1920:r=30:d={duration:.3f}"])
        if narration_available:
            command.extend(["-i", str(audio_path)])
        command.extend(["-i", str(music_path)])
        music_index = 2 if narration_available else 1
        command.extend(["-vf", filter_graph])
        if narration_available:
            command.extend([
                "-filter_complex", f"[1:a]volume=1.0[narration];[{music_index}:a]volume=0.28[music];[narration][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]",
                "-map", "0:v:0",
                "-map", "[mixed]",
            ])
        elif source_background:
            command.extend(["-map", "0:v:0", "-map", "0:a:0"])
        else:
            command.extend(["-map", "0:v:0", "-map", "1:a:0"])
        command.extend([
            "-shortest",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path.resolve()),
        ])
        subprocess.run(command, cwd=temp_dir, check=True)
    return output_path


_THUMB_SCENES = (
    "a neon-lit sports car drifting through a rain-soaked tropical beachfront boulevard at night",
    "a speedboat launching off a wave toward a glowing Miami-style skyline at sunset",
    "a helicopter circling palm-lined skyscrapers under a hot pink and cyan sunset",
    "a lowrider convertible cruising a palm-tree street under a giant orange sun",
    "a dramatic thunderstorm over a neon beach city with a lone motorcycle rider",
    "a heist crew silhouette in front of a glowing vault door in a retro neon garage",
    "a jet ski chase through a canal lined with pastel art-deco hotels at dusk",
    "a police chase of a muscle car on a coastal highway with red and blue lights",
    "a rooftop party overlooking a glittering tropical city skyline at night",
    "a sunset airboat ride through swamp wetlands with distant city lights",
)


def _thumbnail_art(script_path: Path, accent: str) -> Path | None:
    """Generate unique original art for this video; None means use the stock artwork."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or os.getenv("SPECTRE_THUMB_GEN") != "1":
        return None
    out = Path("output/thumb-art") / f"{script_path.stem}.png"
    if out.exists():
        return out
    scene = _THUMB_SCENES[sum(map(ord, script_path.stem)) % len(_THUMB_SCENES)]
    prompt = (
        f"Cinematic 16:9 YouTube thumbnail background, original retro-neon crime-city game art style: {scene}. "
        f"Vivid {accent} and pink neon color grade, high contrast, dramatic lighting, empty space in the lower left. "
        "Original characters and vehicles only. Absolutely no text, letters, logos or watermarks."
    )
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version="v1beta", timeout=120000))
    for model in ("gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview", "gemini-2.5-flash-image"):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(part.inline_data.data)
                    print(f"Thumbnail art generated with {model}", flush=True)
                    return out
        except Exception as exc:
            print(f"Thumbnail art via {model} failed: {str(exc)[:120]}", flush=True)
    return None


def create_thumbnail(script_path: str | Path) -> Path:
    """Render a clickbait 1280x720 thumbnail: unique generated art plus a punchy hook."""
    script_path = Path(script_path)
    ffmpeg = _ffmpeg_tool("ffmpeg")
    images = sorted(p for p in SOURCE_ASSET_DIR.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not ffmpeg or not images:
        raise RuntimeError("Thumbnail needs FFmpeg and original artwork in assets/original-visuals.")
    markdown = script_path.read_text(encoding="utf-8")
    title = _plain_text(_section(markdown, "Title")).upper()
    hook = _plain_text(_section(markdown, "Thumbnail")).upper()
    text = "\n".join(textwrap.wrap(hook, width=13)) if hook else _cover_text(markdown, title)
    seed = sum(map(ord, script_path.stem))
    accent_name, accent_hex = (("cyan", "0x00E5FF"), ("hot orange", "0xFF7A00"), ("lime green", "0x7CFF2E"), ("magenta", "0xFF2E88"))[seed % 4]
    image = _thumbnail_art(script_path, accent_name)
    if image is None:
        # Rotate through the artwork bank in publishing order so neighbouring videos never match.
        used = len(list(Path("output/thumbnails").glob("*.jpg"))) if Path("output/thumbnails").is_dir() else seed
        image = images[used % len(images)]
    out_dir = Path("output/thumbnails")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{script_path.stem}.jpg"
    lines = text.count("\n") + 1
    size = 150 if lines <= 2 else 118
    with tempfile.TemporaryDirectory(prefix="spectre-thumb-") as temp_name:
        temp_dir = Path(temp_name)
        (temp_dir / "t.txt").write_text(text, encoding="utf-8")
        vf = (
            "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            "eq=saturation=1.45:contrast=1.2,"
            "drawbox=x=0:y=0:w=iw:h=ih:color=0x000000@0.18:t=fill,"
            "drawbox=x=0:y=ih-330:w=iw:h=330:color=0x000000@0.55:t=fill,"
            f"drawbox=x=0:y=0:w=iw:h=ih:color={accent_hex}@1:t=14,"
            f"drawtext=fontfile='{FONT}':textfile=t.txt:fontcolor=0xFFE600:fontsize={size}:"
            "line_spacing=8:borderw=12:bordercolor=black:shadowx=6:shadowy=6:x=50:y=h-text_h-60"
        )
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(image.resolve()),
             "-vf", vf, "-frames:v", "1", "-q:v", "3", str(out.resolve())],
            cwd=temp_dir, check=True,
        )
    return out
