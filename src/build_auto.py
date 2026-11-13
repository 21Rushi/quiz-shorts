"""Build today's 7:47 PM Short (Facts or 1-min story) from studio/auto_shorts.json.

Runs inside GitHub Actions before post_premade.py, so no Claude run and no laptop
are needed. If premade/<date>/evening/ already has a video (pushed by hand or by
Claude), that one wins and nothing is built.

Each entry in studio/auto_shorts.json:
  {"date": "YYYY-MM-DD", "kind": "facts" | "story", "tag": "DID YOU KNOW?",
   "topic": "...", "accent": [r, g, b],
   "title_en": "...", "title_hi": "...", "desc_en": "...", "desc_hi": "...",
   "hashtags": "#a #b #shorts", "tags": [...],
   "beats": [{"scene": "3 FACTS", "en": "...", "hi": "...", "vo": "<spoken Hindi>"}, ...]}
facts: 4 beats (hook 5s, facts 10s, last 11s = 36s). story: 6 beats (9s each, last 12s = 57s).

Facts Shorts are VISUAL (from 2026-11-14): every fact is shown over real full-screen pictures
(Wikimedia Commons, planned in studio/facts_visuals.json, fetched by src/visuals.py) with a slow
zoom, and the hook is a fast montage of them. If a picture can't be fetched, that fact falls
back to the old big-text scene, so a video is always produced.

--clips c1.mp4 c2.mp4 c3.mp4 : use three Google Flow clips (one per fact) instead of pictures.
That version is marked as AI-made ("synthetic": true) for YouTube's altered-content label.

Usage: python src/build_auto.py --date YYYY-MM-DD [--dir premade] [--clips c1 c2 c3] [--force]
Exit 0 always (missing entry just means nothing is built).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = "https://www.youtube.com/@I-mRushi?sub_confirmation=1"
VOICE = "hi-IN-MadhurNeural"


def timings(entry):
    n = len(entry["beats"])
    if entry["kind"] == "facts":
        lens = [5.0] + [10.0] * (n - 2) + [11.0]
    else:
        L = entry.get("beat_len", 9.0)
        lens = [L] * (n - 1) + [L + 3.0]
    out, t = [], 0.0
    for L in lens:
        out.append((t, t + L))
        t += L
    return out, t


def media_plan(entry, folder, clips):
    """Full-screen visuals per beat: [hook items, fact 1 items, ...] ([] = keep the text scene)
    plus picture credit lines for the description."""
    n_facts = len(entry["beats"]) - 1
    if clips:
        facts = [[{"kind": "video", "path": os.path.abspath(c)}] for c in clips[:n_facts]]
        hook = [{"kind": "video", "path": os.path.abspath(c), "ss": 2.5} for c in clips[:n_facts]]
        return [hook] + facts + [[]] * (n_facts - len(facts)), []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import visuals
        got = visuals.fetch_for(entry["date"], os.path.join(folder, "img"),
                                os.path.join(ROOT, "studio", "facts_visuals.json"))
    except Exception as e:  # never let pictures stop the upload
        print(f"::warning title=Facts pictures skipped::{type(e).__name__}: {e}")
        return [[]] * (n_facts + 1), []
    got = (got + [[]] * n_facts)[:n_facts]
    facts = [[{"kind": "image", "path": os.path.abspath(im["path"])} for im in b] for b in got]
    hook = [b[-1] for b in facts if b]          # quick montage: one picture from each fact
    return [hook if len(hook) >= 2 else []] + facts, visuals.credits(got)


def build(entry, folder, clips=None):
    spans, total = timings(entry)
    os.makedirs(folder, exist_ok=True)
    media, credit = media_plan(entry, folder, clips) if entry["kind"] == "facts" else ([], [])
    beats, lines = [], []
    for i, ((a, b), bt) in enumerate(zip(spans, entry["beats"])):
        items = media[i] if i < len(media) else []
        if items and i == 0:
            scene = {"type": "media", "items": items, "text": bt["scene"]}
        elif items:
            scene = {"type": "media", "items": items, "label": bt["scene"]}
        else:
            scene = {"type": "big", "text": bt["scene"]}
        beats.append({"start": a, "end": b, "scene": scene, "en": bt["en"], "hi": bt["hi"]})
        lines.append({"start": round(a + 0.3, 2), "text": bt["vo"]})
    spec = {"type": "story", "tag": entry.get("tag", "DID YOU KNOW?"), "duration": total,
            "accent": entry.get("accent", [120, 60, 220]), "beats": beats}
    if entry.get("theme"):
        spec["theme"] = entry["theme"]
    spec_p = os.path.join(folder, "spec.json")
    json.dump(spec, open(spec_p, "w", encoding="utf-8"), ensure_ascii=False)
    raw = os.path.join(folder, "raw.mp4")
    subprocess.run([sys.executable, os.path.join(ROOT, "studio", "engine.py"), spec_p, raw], check=True)
    # Re-encode for YouTube (built inside Actions, so file size is not limited by git).
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-c:v", "libx264", "-preset", "slow",
                    "-b:v", "2600k", "-maxrate", "3000k", "-bufsize", "5000k", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", os.path.join(folder, "video.mp4")], check=True)
    os.remove(raw)
    shutil.rmtree(os.path.join(folder, "img"), ignore_errors=True)
    pics = ("\n\n📷 Photos: Wikimedia Commons - " + "; ".join(credit)) if credit else ""
    if len(pics) > 900:
        pics = pics[:897] + "..."
    q_en = "Which fact shocked you the most? Comment below!" if entry["kind"] == "facts" \
        else "What do you think? Tell me in the comments!"
    q_hi = "कौन सा फैक्ट सबसे चौंकाने वाला लगा? कमेंट करें!" if entry["kind"] == "facts" \
        else "आपका क्या सोचना है? कमेंट में बताइए!"
    meta = {
        "title": entry["title_en"],
        "description": f"{entry['desc_en']}\n\n👇 {q_en}\n\n🔔 Subscribe for daily quizzes + facts: {SUB}\n\n{entry['hashtags']}{pics}",
        "tags": entry["tags"],
        "synthetic": bool(clips),
        "language": "hi",
        "title_language": "en",
        "type": entry["kind"],
        "topic": entry["topic"],
        "localizations": {"hi": {
            "title": entry["title_hi"],
            "description": f"{entry['desc_hi']}\n\n👇 {q_hi}\n\n🔔 रोज़ क्विज़ + फैक्ट्स के लिए Subscribe करें: {SUB}\n\n{entry['hashtags']}"}},
        "voiceover": {"voice": VOICE, "lines": lines},
    }
    json.dump(meta, open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Built {entry['kind']} Short for {entry['date']}: {entry['title_en']} ({total:.0f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dir", default="premade")
    ap.add_argument("--clips", nargs="*", default=None, help="Google Flow clips, one per fact")
    ap.add_argument("--force", action="store_true", help="rebuild even if a video already exists")
    a = ap.parse_args()
    folder = os.path.join(a.dir, a.date, "evening")
    if os.path.isfile(os.path.join(folder, "video.mp4")) and not a.force:
        print(f"Pre-made video already exists for {a.date} - not building.")
        return 0
    entries = json.load(open(os.path.join(ROOT, "studio", "auto_shorts.json"), encoding="utf-8"))
    entry = next((e for e in entries if e["date"] == a.date), None)
    if not entry:
        print(f"No auto Short planned for {a.date}.")
        return 0
    if entry["kind"] == "story":
        # 1-min stories are made only in Google Flow (realistic) by the Sunday Flow task.
        # No plain code-made fallback: if Flow wasn't pushed, the slot waits for a manual run.
        print(f"{a.date} is a Flow story day - waiting for the Google Flow video, not building a plain one.")
        return 0
    build(entry, folder, a.clips)
    return 0


if __name__ == "__main__":
    sys.exit(main())
