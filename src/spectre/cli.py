import argparse
import os
import sys

from dotenv import load_dotenv

from .daily import run_daily
from .generator import CATEGORIES, generate_script
from .youtube import authenticate, upload_video


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(prog="spectre", description="SPECTRE Gaming Agent: scripts and private YouTube drafts")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a Short script with Gemini")
    gen.add_argument("--topic", required=True)
    gen.add_argument("--category", choices=sorted(CATEGORIES), default="entertaining-short")
    gen.add_argument("--notes", default="", help="Optional facts/source notes for you to verify")

    sub.add_parser("youtube-auth", help="Authorize this Mac for YouTube uploads")

    up = sub.add_parser("upload", help="Upload a finished video as a private draft")
    up.add_argument("--video", required=True)
    up.add_argument("--title", required=True)
    up.add_argument("--description", default="")
    up.add_argument("--tags", default="", help="Comma-separated tags")
    up.add_argument("--confirm-upload", action="store_true", help="Required when REQUIRE_UPLOAD_CONFIRMATION=true")

    daily = sub.add_parser("daily", help="Generate a sourced pre-launch Short and optionally upload it")
    daily.add_argument("--slot", required=True, help="Run the scheduled content slot")
    daily.add_argument("--no-upload", action="store_true", help="Render the video without uploading it")
    daily.add_argument("--visibility", choices=["private", "public", "unlisted"], default="private")

    sub.add_parser("queue-tick", help="Publish the next reviewed Short if due, then top the review queue back up to 4")

    qp = sub.add_parser("queue-publish", help="Publish a queued Short now (oldest unless --seq)")
    qp.add_argument("--seq", type=int)
    qr = sub.add_parser("queue-rerender", help="Re-render a queued Short")
    qr.add_argument("--seq", type=int, required=True)
    sub.add_parser("queue-refill", help="Render until the review queue is full")

    args = parser.parse_args()
    try:
        if args.command == "generate":
            path = generate_script(args.topic, args.category, args.notes)
            print(f"Saved script: {path}")
        elif args.command == "youtube-auth":
            path = authenticate()
            print(f"YouTube authorization saved locally: {path}")
        elif args.command == "upload":
            if os.getenv("REQUIRE_UPLOAD_CONFIRMATION", "false").lower() == "true" and not args.confirm_upload:
                raise RuntimeError("Set REQUIRE_UPLOAD_CONFIRMATION=false or rerun with --confirm-upload after reviewing the upload details.")
            video_id = upload_video(args.video, args.title, args.description, [x.strip() for x in args.tags.split(",") if x.strip()])
            print(f"Private YouTube draft created: https://youtu.be/{video_id}")
        elif args.command == "queue-publish":
            from .review_queue import publish_item
            print(publish_item(args.seq) or "nothing to publish")
        elif args.command == "queue-rerender":
            from .review_queue import rerender
            rerender(args.seq)
        elif args.command == "queue-refill":
            from .review_queue import refill
            refill()
        elif args.command == "queue-tick":
            from .review_queue import tick
            tick()
        elif args.command == "daily":
            result = run_daily(args.slot, upload=not args.no_upload, visibility=args.visibility)
            print(f"Script: {result['script']}")
            print(f"Video: {result['video']}")
            if result.get("youtube_url"):
                print(f"YouTube video: {result['youtube_url']}")
    except KeyboardInterrupt:
        print("\nCancelled. No script was saved.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
