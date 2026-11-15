from datetime import datetime
from pathlib import Path
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types


CATEGORIES = {
    "gaming-news": "Gaming news, clearly separating confirmed reporting from rumor.",
    "gta-theory": "GTA VI theories, explicitly labeled as fan speculation unless verified.",
    "countdown": "A countdown or milestone update; do not invent release dates or remaining days.",
    "gaming-fact": "An entertaining gaming fact with a checkable factual claim.",
    "entertaining-short": "A punchy, entertaining gaming Short with a strong opening hook.",
}


def generate_script(topic: str, category: str, notes: str = "") -> Path:
    load_dotenv()
    import os

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "180"))
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
    )
    prompt = f"""You are the SPECTRE Gaming channel's Shorts writer.
Create a fresh 30-45 second vertical-video package. Category: {category} ({CATEGORIES[category]})
Topic: {topic}
Creator-provided notes (treat as context, not guaranteed truth): {notes or 'None'}

Style: high-curiosity, punchy, and click-worthy, while staying accurate and genuinely useful. Every title must be an accurate clickbait hook: create urgency, tension, a surprising specific detail, or a clear benefit that the video delivers. Use 45-70 characters when practical. Do not use generic titles, dishonest claims, fake leaks, or words such as "confirmed" unless the source notes support them. The narration must deliver a specific takeaway or explain why a detail matters; ban vague filler such as "fans are talking" or "this changes everything." Do not invent leaks, fan observations, gameplay mechanics, quotes, dates, or trailer details. Treat the supplied source notes as the only confirmed facts. If a timely factual claim has no source in the notes, mark it for verification and do not state it as confirmed. Label every theory as speculation and make the title match what the narration actually supports.

Return these sections in Markdown:
## Title (under 70 characters)
## Hook (first 1-2 seconds)
## Voiceover (about 75-110 spoken words)
## Visual beats (3-5 concise lines in this exact format: `SHORT LABEL | useful on-screen copy (max 8 words) | specific graphic/shot idea`; the last field is an edit instruction, not text to show viewers. Use only footage the creator has rights to.)
## On-screen captions
## Description
## Hashtags (3-5)
## Sources (URLs from the creator-provided notes; omit if none)
## Fact check before recording

Do not claim to have browsed or verified anything. Never present rumors or theories as confirmed facts. Make visual beats concrete enough to render as clear on-screen scene cards, not generic instructions like "show related footage." Keep useful on-screen copy separate from edit instructions. Avoid repetitive templates: vary the hook, explanation, payoff, and visual concept for each topic.
For live news or countdowns, identify facts the creator must verify and avoid unsupported dates or numbers.
"""
    print(f"Contacting Gemini for the script (up to {timeout_seconds} seconds)...", flush=True)
    response = client.models.generate_content(model=model, contents=prompt)
    body = (response.text or "").strip()
    if not body:
        raise RuntimeError("Gemini returned an empty response.")

    safe_topic = re.sub(r"[^a-zA-Z0-9]+", "-", topic).strip("-").lower()[:48] or "short"
    out_dir = Path("output/scripts")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_topic}.md"
    path.write_text(f"# SPECTRE Gaming Agent — {category}\n\nTopic: {topic}\n\n{body}\n", encoding="utf-8")
    return path
