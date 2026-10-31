"""Add a spoken voiceover to a pre-made Short (used for Facts videos).

meta.json may contain:
  "voiceover": {
      "voice": "hi-IN-MadhurNeural",          # optional, default below
      "rate": "+0%",                           # optional edge-tts speaking rate
      "music_volume": 0.3,                     # optional, background music level under the voice
      "lines": [{"start": 0.3, "text": "..."}, ...]   # start = seconds into the video
  }

Each line is spoken with Microsoft Edge neural TTS (edge-tts, free, needs internet - works
in GitHub Actions), sped up slightly if it would run into the next line, placed at its start
time, and mixed over the original music (which is lowered). The video stream is copied as-is.

Usage: python src/voiceover.py in.mp4 meta.json out.mp4
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile

DEFAULT_VOICE = "hi-IN-MadhurNeural"
MAX_TEMPO = 1.35


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def tts(text, voice, rate, path):
    import edge_tts
    err = "empty audio"
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(path)
            if os.path.getsize(path) > 0:
                return
        except Exception as e:  # network hiccup - retry
            err = e
        await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"TTS failed for line: {text[:40]}... ({err})")


def add_voiceover(video, vo, out):
    lines = [l for l in vo.get("lines", []) if l.get("text", "").strip()]
    if not lines:
        raise ValueError("voiceover has no lines")
    lines.sort(key=lambda l: float(l["start"]))
    voice, rate = vo.get("voice", DEFAULT_VOICE), vo.get("rate", "+0%")
    music = float(vo.get("music_volume", 0.3))
    total = duration(video)
    tmp = tempfile.mkdtemp(prefix="vo_")
    clips = []
    for i, l in enumerate(lines):
        p = os.path.join(tmp, f"l{i}.mp3")
        asyncio.run(tts(l["text"], voice, rate, p))
        start = float(l["start"])
        end = float(lines[i + 1]["start"]) if i + 1 < len(lines) else total
        room = max(0.5, end - start - 0.15)
        tempo = min(MAX_TEMPO, max(1.0, duration(p) / room))
        clips.append((p, start, tempo))
        print(f"  line {i + 1}: {start:.1f}s, {duration(p):.1f}s audio, tempo {tempo:.2f}")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video]
    for p, _, _ in clips:
        cmd += ["-i", p]
    parts = [f"[0:a]volume={music}[m]"]
    for i, (_, start, tempo) in enumerate(clips, 1):
        d = int(start * 1000)
        parts.append(f"[{i}:a]aresample=44100,atempo={tempo:.3f},volume=1.6,adelay={d}|{d}[v{i}]")
    mix = "[m]" + "".join(f"[v{i}]" for i in range(1, len(clips) + 1))
    parts.append(f"{mix}amix=inputs={len(clips) + 1}:duration=first:normalize=0,alimiter=limit=0.95[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(f"Voiceover added ({len(clips)} lines, voice {voice}) -> {out}")
    return out


if __name__ == "__main__":
    meta = json.load(open(sys.argv[2], encoding="utf-8"))
    add_voiceover(sys.argv[1], meta["voiceover"], sys.argv[3])
