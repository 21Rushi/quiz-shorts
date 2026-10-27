"""Weekly long-form GK challenge (16:9, ~10 minutes, 40 questions).

Why: Shorts views and long-form watch hours are separate monetisation paths.
A weekly 8+ minute video builds watch hours, qualifies for mid-roll ads once
monetised, and sends viewers from Shorts to a longer session on the channel.

Usage:
  python src/weekly.py --dry-run            # render this week's video only
  python src/weekly.py                      # render + upload
  python src/weekly.py --count 6 --dry-run  # quick short test render
"""
import argparse
import datetime as dt
import json
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import music  # noqa: E402
from make_video import FONT_BOLD, FONT_MED, ROOT, font, render_frames  # noqa: E402

CONFIG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
W, H = 1920, 1080
THINK, SHOW = 10.0, 4.0          # seconds to think, seconds showing the answer
SEG = THINK + SHOW
INTRO, OUTRO = 4.0, 8.0
BG = ((34, 18, 84), (10, 6, 34))
ACCENT = (255, 196, 0)


def week_number(today):
    start = dt.date.fromisoformat(CONFIG["start_date"])
    return max(1, (today - start).days // 7 + 1)


def pick_questions(week, count):
    qs = json.load(open(os.path.join(ROOT, "questions.json"), encoding="utf-8"))
    sched = {s["q"] for s in json.load(open(os.path.join(ROOT, "schedule.json"), encoding="utf-8"))}
    pool = [q for q in qs if q["q"] not in sched]
    random.Random(2026).shuffle(pool)            # fixed order, so weeks don't repeat until the pool ends
    start = ((week - 1) * count) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(count)]


def gradient_card():
    t = np.linspace(0, 1, H)[:, None, None]
    arr = np.array(BG[0])[None, None, :] * (1 - t) + np.array(BG[1])[None, None, :] * t
    return Image.fromarray(np.repeat(arr, W, axis=1).astype(np.uint8), "RGB")


def centered(d, y, text, fnt, fill):
    w = d.textlength(text, font=fnt)
    d.text(((W - w) / 2, y), text, font=fnt, fill=fill)


def make_card(path, lines):
    img = gradient_card()
    d = ImageDraw.Draw(img)
    for y, text, size, bold, col in lines:
        centered(d, y, text, font(FONT_BOLD if bold else FONT_MED, size), col)
    img.save(path)


def card_video(png, seconds, out, seed):
    wav = out + ".wav"
    music.write_wav(wav, music.background_track(seconds, seed=seed) * 0.8)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav,
                    "-t", str(seconds), "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", out],
                   check=True)
    os.remove(wav)


def widen(vertical_mp4, out):
    """Place a 9:16 segment on a blurred 16:9 copy of itself."""
    vf = ("[0:v]split=2[a][b];"
          "[a]scale=1920:-2,crop=1920:1080,boxblur=30:3,eq=brightness=-0.15[bg];"
          "[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vertical_mp4, "-filter_complex", vf,
                    "-map", "[v]", "-map", "0:a", "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", out], check=True)


def concat(parts, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", out], check=True)
    os.remove(lst)


def thumbnail(path, count, week):
    img = gradient_card().resize((1280, 720))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([60, 60, 1220, 660], 40, outline=ACCENT, width=10)
    def c(y, text, size, col, bold=True):
        f = font(FONT_BOLD if bold else FONT_MED, size)
        w = d.textlength(text, font=f)
        d.text(((1280 - w) / 2, y), text, font=f, fill=col)
    c(110, f"{count} GK QUESTIONS", 120, (255, 255, 255))
    c(290, "Can you score", 70, (255, 255, 255), False)
    c(380, f"{int(count * 0.8)}+?", 160, ACCENT)
    c(590, f"WEEKLY CHALLENGE #{week}", 44, (200, 200, 255))
    img.save(path, quality=92)


def fmt(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--week", type=int, default=None)
    args = ap.parse_args()

    week = args.week or week_number(dt.datetime.now(IST).date())
    qs = pick_questions(week, args.count)
    work = os.path.join(ROOT, "out", f"weekly_{week:03d}")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    print(f"Weekly challenge #{week}: {len(qs)} questions")

    sub_link = "https://www.youtube.com/@I-mRushi?sub_confirmation=1"
    make_card(f"{work}/intro.png", [
        (250, f"{len(qs)} GK QUESTIONS", 120, True, (255, 255, 255)),
        (430, "10 seconds each — keep score!", 60, False, (230, 230, 255)),
        (560, "Comment your score at the end", 56, True, ACCENT),
    ])
    make_card(f"{work}/outro.png", [
        (200, "How many did you get right?", 84, True, (255, 255, 255)),
        (360, "Comment your score below!", 64, False, ACCENT),
        (520, "Subscribe for 2 new quizzes every day", 56, True, (255, 255, 255)),
        (620, "+ a new 40-question challenge every Sunday", 48, False, (200, 200, 255)),
    ])
    parts = []
    card_video(f"{work}/intro.png", INTRO, f"{work}/00_intro.mp4", seed=week)
    parts.append(f"{work}/00_intro.mp4")

    for i, q in enumerate(qs, 1):
        q = dict(q)
        q["id"] = 5000 + week * 100 + i       # fresh colours/option order per appearance
        v = f"{work}/q{i:02d}_v.mp4"
        render_frames(q, i, v, os.path.join(ROOT, "assets/music"), reveal_at=THINK, duration=SEG,
                      label=f"QUESTION {i}/{len(qs)}")
        wide = f"{work}/q{i:02d}.mp4"
        widen(v, wide)
        os.remove(v)
        parts.append(wide)
        print(f"  rendered {i}/{len(qs)}", flush=True)

    card_video(f"{work}/outro.png", OUTRO, f"{work}/99_outro.mp4", seed=week + 1)
    parts.append(f"{work}/99_outro.mp4")
    final = os.path.join(ROOT, "out", f"weekly_challenge_{week:03d}.mp4")
    concat(parts, final)
    thumb = os.path.join(ROOT, "out", f"weekly_thumb_{week:03d}.jpg")
    thumbnail(thumb, len(qs), week)

    # chapters every 5 questions (YouTube needs 0:00 first and >=10 s each)
    chapters = ["0:00 Start"]
    for i in range(0, len(qs), 5):
        chapters.append(f"{fmt(INTRO + i * SEG)} Questions {i + 1}–{min(i + 5, len(qs))}")
    chapters.append(f"{fmt(INTRO + len(qs) * SEG)} Your score")
    title = f"{len(qs)} GK Questions — Can You Score {int(len(qs) * 0.8)}+? 🧠 Weekly GK Challenge #{week}"
    desc = (f"🧠 Weekly GK Challenge #{week}: {len(qs)} general knowledge questions, 10 seconds each.\n"
            f"Keep score and comment it at the end!\n\n" + "\n".join(chapters) +
            f"\n\n🔔 Subscribe for 2 new quiz Shorts every day + a new challenge every Sunday: {sub_link}\n\n"
            "#gkquiz #generalknowledge #quiz #trivia #gk #quizchallenge")
    tags = CONFIG["tags"] + ["gk challenge", "40 gk questions", "general knowledge quiz", "trivia challenge"]
    print("Title:", title)
    shutil.rmtree(work, ignore_errors=True)

    if args.dry_run:
        print("Dry run - not uploading. Video at", final)
        return
    from youtube_upload import get_service, upload

    privacy = os.environ.get("YT_PRIVACY", CONFIG.get("privacy", "public"))
    now = dt.datetime.now(IST)
    when = now.replace(hour=20, minute=47, second=0, microsecond=0)   # Sunday 8:47 PM IST
    publish_at = when if privacy == "public" and when > now + dt.timedelta(minutes=3) else None
    print("Scheduled to go public at", when.strftime("%d %b %H:%M IST") if publish_at else "now")
    vid = upload(final, title, desc, tags, privacy=privacy, publish_at=publish_at)
    print(f"Uploaded: https://youtu.be/{vid}")
    try:
        from googleapiclient.http import MediaFileUpload
        get_service().thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
        print("Custom thumbnail set")
    except Exception as e:  # needs a phone-verified channel; the video is fine without it
        print(f"::warning title=Thumbnail not set::{type(e).__name__}: {str(e)[:300]}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Weekly challenge #{week}\nhttps://youtu.be/{vid}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"::error title=Weekly upload failed::{type(e).__name__}: {str(e)[:900]}")
        raise
