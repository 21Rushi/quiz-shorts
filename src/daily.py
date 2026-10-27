"""Pick the quiz for today's slot, render the Short and upload it.

Two slots a day: morning and evening.
  1. If schedule.json has an entry for (today, slot) -> use it (bilingual, topical).
  2. Otherwise fall back to questions.json in rotation (English only), so the
     channel never goes quiet once the 21-day plan runs out.

Usage:
  python src/daily.py --slot morning            # render + upload
  python src/daily.py --slot evening --dry-run  # render only
  python src/daily.py --date 2026-11-08 --slot morning --dry-run   # preview any day
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from make_video import ROOT, render_frames  # noqa: E402

CONFIG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
SLOTS = ["morning", "evening"]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def today_ist():
    return dt.datetime.now(IST).date()


def slot_from_clock():
    return "morning" if dt.datetime.now(IST).hour < 13 else "evening"


def pick(day, slot):
    start = dt.date.fromisoformat(CONFIG["start_date"])
    day_no = max(0, (day - start).days)
    slot_i = SLOTS.index(slot)
    episode = day_no * len(SLOTS) + slot_i + 1 + CONFIG.get("episode_offset", 0)

    schedule = json.load(open(os.path.join(ROOT, "schedule.json"), encoding="utf-8"))
    for i, item in enumerate(schedule):
        if item["date"] == day.isoformat() and item["slot"] == slot:
            q = dict(item)
            q["id"] = 1000 + i
            return q, episode

    questions = json.load(open(os.path.join(ROOT, "questions.json"), encoding="utf-8"))
    used = {s["q"] for s in schedule}
    pool = [q for q in questions if q["q"] not in used] or questions
    return dict(pool[(day_no * len(SLOTS) + slot_i) % len(pool)]), episode


def metadata(q, episode, opts, opts_hi):
    labels = "ABCD"
    bilingual = bool(q.get("q_hi"))
    title = CONFIG["title_template"].format(episode=episode, question=q["q"])
    if len(title) > 100:
        title = CONFIG["title_fallback"].format(episode=episode)

    lines = []
    for i, o in enumerate(opts):
        hi = opts_hi[i] if bilingual and opts_hi[i] != o else None
        lines.append(f"{labels[i]}) {o}" + (f" / {hi}" if hi else ""))
    question_block = q["q"] + (f"\n{q['q_hi']}" if bilingual else "")
    extra_tags = q.get("tags", [])
    hashtags = " ".join("#" + t.replace(" ", "").replace("'", "") for t in extra_tags[:3])
    desc = CONFIG["description_template"].format(
        episode=episode, question=question_block, options="\n".join(lines),
        category=q["c"], topic_hashtags=hashtags,
    )
    tags = CONFIG["tags"] + (CONFIG["tags_hindi"] if bilingual else []) + extra_tags + [q["c"].lower() + " quiz"]
    # YouTube caps all tags combined at 500 characters
    out, total = [], 0
    for t in dict.fromkeys(tags):
        if total + len(t) + 2 > 480:
            break
        out.append(t)
        total += len(t) + 2
    return title, desc, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=SLOTS, default=None, help="defaults to the current IST half of the day")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today (IST)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    day = dt.date.fromisoformat(args.date) if args.date else today_ist()
    slot = args.slot or slot_from_clock()
    q, episode = pick(day, slot)
    out = os.path.join(ROOT, "out", f"quiz_{episode:04d}_{slot}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"{day} {slot} | Episode #{episode} | [{q['c']}] {q['q']}")
    info = render_frames(q, episode, out, os.path.join(ROOT, "assets/music"))
    title, desc, tags = metadata(q, episode, info["options"], info["options_hi"])
    print("Title:", title)

    if args.dry_run:
        print("Dry run - not uploading. Video at", out)
        return
    from youtube_upload import upload  # imported late so dry runs need no Google libs

    vid = upload(out, title, desc, tags, privacy=os.environ.get("YT_PRIVACY", CONFIG.get("privacy", "public")))
    print(f"Uploaded: https://youtube.com/shorts/{vid}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Quiz #{episode} ({slot})\n{q['q']}\n\nhttps://youtube.com/shorts/{vid}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # surface the reason as a GitHub annotation
        msg = f"{type(e).__name__}: {e}".replace("\n", " ")[:900]
        print(f"::error title=Quiz upload failed::{msg}")
        raise
