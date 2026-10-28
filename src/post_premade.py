"""Upload a pre-made Short (Flow story or Facts) for a date + slot, if one exists.

Pre-made videos live on the `premade` branch, which the workflow checks out into
./premade. Layout:
  premade/<YYYY-MM-DD>/<slot>/video.mp4
  premade/<YYYY-MM-DD>/<slot>/meta.json
      {"title": "...", "description": "...", "tags": [...],
       "synthetic": true|false,   # YouTube AI label: true for realistic AI (Flow/Veo)
       "language": "hi" | "en"}

Exit codes: 0 = uploaded (or dry run), 3 = nothing pre-made for this date+slot.

Usage:
  python src/post_premade.py --slot evening [--date YYYY-MM-DD] [--dir premade] [--dry-run]
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from daily import PUBLISH_TIMES, IST, CONFIG, today_ist  # noqa: E402

NONE_FOUND = 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=list(PUBLISH_TIMES), required=True)
    ap.add_argument("--date", default=None)
    ap.add_argument("--dir", default="premade")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    day = dt.date.fromisoformat(a.date) if a.date else today_ist()
    folder = os.path.join(a.dir, day.isoformat(), a.slot)
    video, meta_p = os.path.join(folder, "video.mp4"), os.path.join(folder, "meta.json")
    if not (os.path.isfile(video) and os.path.isfile(meta_p)):
        print(f"No pre-made video for {day} {a.slot} - falling back to the quiz.")
        return NONE_FOUND

    meta = json.load(open(meta_p, encoding="utf-8"))
    title, desc = meta["title"], meta["description"]
    tags, total, out = meta.get("tags", []), 0, []
    for t in dict.fromkeys(tags):  # YouTube caps tags at 500 chars total
        if total + len(t) + 2 > 480:
            break
        out.append(t)
        total += len(t) + 2
    synthetic = bool(meta.get("synthetic", False))
    print(f"{day} {a.slot} | pre-made | {title} | AI label: {synthetic}")
    if a.dry_run:
        print("Dry run - not uploading.")
        return 0

    from youtube_upload import upload
    privacy = os.environ.get("YT_PRIVACY", CONFIG.get("privacy", "public"))
    h, m = PUBLISH_TIMES[a.slot]
    when = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=IST)
    publish_at = when if privacy == "public" and when > dt.datetime.now(IST) + dt.timedelta(minutes=3) else None
    vid = upload(video, title, desc, out, privacy=privacy, publish_at=publish_at,
                 synthetic=synthetic, language=meta.get("language", "en"))
    print(f"Uploaded: https://youtube.com/shorts/{vid}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Pre-made ({a.slot})\n{title}\n\nhttps://youtube.com/shorts/{vid}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        msg = f"{type(e).__name__}: {e}".replace("\n", " ")[:900]
        print(f"::error title=Pre-made upload failed::{msg}")
        raise
