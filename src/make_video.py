"""Render one quiz question into a vertical YouTube Short (1080x1920).

Timeline (default):
  0.0s  question + options slide in, 25s countdown starts
  20s   ticking speeds the tension up
  25s   ANSWER REVEAL: correct option turns green, chime, fun fact
  31s   end
"""
import argparse
import glob
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import music  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
REVEAL_AT = 25.0
DURATION = 31.0
TICK_FROM = 20.0

FONT_BOLD = os.path.join(ROOT, "assets/fonts/Poppins-Bold.ttf")
FONT_MED = os.path.join(ROOT, "assets/fonts/Poppins-Medium.ttf")
FONT_HI_BOLD = os.path.join(ROOT, "assets/fonts/NotoSansDevanagari-Bold.ttf")
FONT_HI_MED = os.path.join(ROOT, "assets/fonts/NotoSansDevanagari-Medium.ttf")

THEMES = [  # (top, bottom, accent)
    ((38, 20, 92), (12, 8, 40), (255, 196, 0)),
    ((10, 54, 96), (4, 16, 40), (0, 220, 200)),
    ((92, 16, 70), (30, 6, 34), (255, 120, 180)),
    ((20, 70, 50), (4, 24, 18), (170, 255, 120)),
    ((96, 40, 10), (34, 10, 4), (255, 200, 90)),
]
HOOKS = [
    "Only 1 in 10 get this right!",
    "Can you beat the timer?",
    "Most people get this wrong!",
    "Think fast!",
    "Are you smarter than average?",
    "Quick! 25 seconds!",
    "Test your brain!",
]
HOOKS_HI = [
    "सिर्फ़ 10% लोग सही जवाब देते हैं!",
    "क्या आप टाइमर से तेज़ हैं?",
    "ज़्यादातर लोग यहाँ गलती करते हैं!",
    "जल्दी सोचिए!",
    "अपना GK टेस्ट कीजिए!",
    "25 सेकंड में जवाब दीजिए!",
    "देखते हैं आप कितने होशियार हैं!",
]
GREEN = (34, 197, 94)
# Layout keeps everything inside the Shorts "safe zone": YouTube overlays the
# title/channel at the bottom (~y>1650) and action buttons on the right edge.
OPT_X, OPT_W, OPT_H = 60, 860, 136
OPT_Y0, OPT_STEP = 772, 150
HOOK_Y = 268
FACT_Y = 1385
RED_DIM = (255, 255, 255, 70)


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, path, max_w, max_h, start=86, min_size=40, spacing=1.18):
    size = start
    while size >= min_size:
        f = font(path, size)
        lines = wrap(draw, text, f, max_w)
        lh = int(size * spacing)
        if lh * len(lines) <= max_h:
            return f, lines, lh
        size -= 3
    f = font(path, min_size)
    return f, wrap(draw, text, f, max_w), int(min_size * spacing)


def shrink(draw, text, path, max_w, start, min_size):
    """Largest single-line font size that fits max_w."""
    size = start
    while size > min_size and draw.textlength(text, font=font(path, size)) > max_w:
        size -= 2
    return font(path, size)


def gradient(top, bottom):
    t = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t)
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(max(x, 0), 1)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def rounded(size, radius, fill, outline=None, width=0):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius, fill=fill, outline=outline, width=width)
    return img


def shadow(img, blur=18, offset=(0, 10), alpha=110):
    sh = Image.new("RGBA", (img.width + blur * 4, img.height + blur * 4), (0, 0, 0, 0))
    mask = img.split()[3].point(lambda a: alpha if a > 0 else 0)
    sh.paste((0, 0, 0, 255), (blur * 2 + offset[0], blur * 2 + offset[1]), mask)
    return sh.filter(ImageFilter.GaussianBlur(blur))


def build_option(label, text, state, accent, text_hi=None):
    """state: normal | correct | wrong"""
    ow, oh = OPT_W, OPT_H
    if state == "correct":
        card = rounded((ow, oh), 36, GREEN + (255,))
        badge_fill, badge_txt, txt_col = (255, 255, 255, 255), GREEN, (255, 255, 255)
    elif state == "wrong":
        card = rounded((ow, oh), 36, (255, 255, 255, 40), outline=(255, 255, 255, 60), width=3)
        badge_fill, badge_txt, txt_col = (255, 255, 255, 50), (255, 255, 255), (255, 255, 255, 110)
    else:
        card = rounded((ow, oh), 36, (255, 255, 255, 235))
        badge_fill, badge_txt, txt_col = accent + (255,), (20, 16, 40), (20, 16, 40)
    d = ImageDraw.Draw(card)
    d.ellipse([20, 20, oh - 20, oh - 20], fill=badge_fill)
    bf = font(FONT_BOLD, 52)
    lw = d.textlength(label, font=bf)
    d.text((oh / 2 - lw / 2, oh / 2 - 38), label, font=bf, fill=badge_txt)
    tx, maxw = oh + 14, ow - oh - 110
    if text_hi and text_hi != text:
        f = shrink(d, text, FONT_BOLD, maxw, 44, 28)
        fh = shrink(d, text_hi, FONT_HI_MED, maxw, 38, 24)
        d.text((tx, oh // 2 + 2), text, font=f, fill=txt_col, anchor="ls")
        d.text((tx, oh // 2 + 50), text_hi, font=fh, fill=txt_col, anchor="ls")
    else:
        f, lines, lh = fit_text(d, text, FONT_BOLD, maxw, oh - 24, start=54, min_size=32, spacing=1.1)
        ty = (oh - lh * len(lines)) // 2 - 4
        for ln in lines:
            d.text((tx, ty), ln, font=f, fill=txt_col)
            ty += lh
    if state == "correct":
        # check mark
        m = oh // 2
        d.line([(ow - 100, m + 4), (ow - 74, m + 30), (ow - 34, m - 26)], fill=(255, 255, 255), width=13, joint="curve")
    return card


def make_static(q, episode, theme, hook):
    top, bottom, accent = theme
    base = gradient(top, bottom)
    d = ImageDraw.Draw(base)
    rng = random.Random(q["id"])
    # soft bokeh blobs
    blobs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for _ in range(9):
        r = rng.randint(80, 260)
        x, y = rng.randint(-100, W + 100), rng.randint(-100, H + 100)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=accent + (rng.randint(10, 28),))
    base = Image.alpha_composite(base, blobs.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(base)

    # header pill
    hf = font(FONT_BOLD, 46)
    label = f"DAILY QUIZ #{episode}"
    tw = d.textlength(label, font=hf)
    pill = rounded((int(tw) + 80, 92), 46, accent + (255,))
    ImageDraw.Draw(pill).text((40, 14), label, font=hf, fill=(20, 16, 40))
    base.alpha_composite(pill, ((W - pill.width) // 2, 105))
    cf = font(FONT_MED, 38)
    cat = q["c"].upper()
    cw = d.textlength(cat, font=cf)
    d.text(((W - cw) / 2, 210), cat, font=cf, fill=(255, 255, 255, 200))

    # hook line
    kf = font(FONT_HI_BOLD if q.get("q_hi") else FONT_BOLD, 50)
    if not hook:
        return finish_static(base, q, d)
    kw = d.textlength(hook, font=kf)
    d.text(((W - kw) / 2 + 3, HOOK_Y + 3), hook, font=kf, fill=(0, 0, 0, 120))
    d.text(((W - kw) / 2, HOOK_Y), hook, font=kf, fill=accent)

    return finish_static(base, q, d)


def finish_static(base, q, d):
    # question card
    qx, qy, qw, qh = 70, 350, 940, 390
    card = rounded((qw, qh), 48, (255, 255, 255, 30), outline=(255, 255, 255, 90), width=4)
    base.alpha_composite(card, (qx, qy))
    hi = q.get("q_hi")
    f, lines, lh = fit_text(d, q["q"], FONT_BOLD, qw - 100, (200 if hi else qh - 80), start=(66 if hi else 82),
                            min_size=40 if hi else 48)
    fh, lines_hi, lhh = (fit_text(d, hi, FONT_HI_BOLD, qw - 100, 130, start=50, min_size=34, spacing=1.45)
                         if hi else (None, [], 0))
    gap = 18 if hi else 0
    block = lh * len(lines) + gap + lhh * len(lines_hi)
    ty = qy + (qh - block) // 2 - 6
    for ln in lines:
        lw = d.textlength(ln, font=f)
        d.text(((W - lw) / 2 + 3, ty + 4), ln, font=f, fill=(0, 0, 0, 110))
        d.text(((W - lw) / 2, ty), ln, font=f, fill=(255, 255, 255))
        ty += lh
    ty += gap
    for ln in lines_hi:
        lw = d.textlength(ln, font=fh)
        d.text(((W - lw) / 2 + 2, ty + 3), ln, font=fh, fill=(0, 0, 0, 110))
        d.text(((W - lw) / 2, ty), ln, font=fh, fill=(255, 236, 170))
        ty += lhh
    return base


def make_fact_card(fact, title_col, fact_hi=None):
    fw, fh = OPT_W, (290 if fact_hi else 250)
    card = rounded((fw, fh), 40, (255, 255, 255, 240))
    d = ImageDraw.Draw(card)
    tf = font(FONT_BOLD, 36)
    d.text((44, 22), "DID YOU KNOW?", font=tf, fill=title_col)
    if fact_hi:
        tw = d.textlength("DID YOU KNOW?  ", font=tf)
        d.text((44 + tw, 18), "क्या आप जानते हैं?", font=font(FONT_HI_BOLD, 32), fill=title_col)
    f, lines, lh = fit_text(d, fact, FONT_MED, fw - 88, (100 if fact_hi else fh - 100), start=40 if fact_hi else 44,
                            min_size=26, spacing=1.2)
    ty = 76
    for ln in lines:
        d.text((44, ty), ln, font=f, fill=(25, 22, 45))
        ty += lh
    if fact_hi:
        ty += 6
        fh_, lines_hi, lhh = fit_text(d, fact_hi, FONT_HI_MED, fw - 88, fh - ty - 10, start=36, min_size=26, spacing=1.45)
        for ln in lines_hi:
            d.text((44, ty), ln, font=fh_, fill=(70, 60, 110))
            ty += lhh
    return card


def draw_timer(frame, t, accent, bilingual=False):
    d = ImageDraw.Draw(frame)
    remaining = max(0.0, REVEAL_AT - t)
    secs = math.ceil(remaining)
    cx, cy, r = OPT_X + OPT_W // 2, 1475, 92
    frac = remaining / REVEAL_AT
    if frac > 0.5:
        col = (34, 197, 94)
    elif frac > 0.2:
        col = (250, 204, 21)
    else:
        col = (239, 68, 68)
    pulse = 1.0
    if remaining <= 5:
        ph = remaining - math.floor(remaining)
        pulse = 1 + 0.10 * max(0, ph - 0.6) / 0.4
    rr = int(r * pulse)
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(0, 0, 0, 90))
    d.arc([cx - rr, cy - rr, cx + rr, cy + rr], 0, 360, fill=(255, 255, 255, 50), width=18)
    d.arc([cx - rr, cy - rr, cx + rr, cy + rr], -90, -90 + 360 * frac, fill=col, width=18)
    nf = font(FONT_BOLD, int(84 * pulse))
    s = str(secs)
    sw = d.textlength(s, font=nf)
    d.text((cx - sw / 2, cy - nf.size * 0.62), s, font=nf, fill=(255, 255, 255))
    col = (255, 255, 255, 215)
    if bilingual:  # Latin and Devanagari need different fonts, so draw two pieces
        en, hi = "Comment your answer  |  ", "कमेंट में जवाब दें"
        fe, fh = font(FONT_MED, 34), font(FONT_HI_MED, 34)
        we, wh = d.textlength(en, font=fe), d.textlength(hi, font=fh)
        x0, base = cx - (we + wh) / 2, cy + r + 58
        d.text((x0, base), en, font=fe, fill=col, anchor="ls")
        d.text((x0 + we, base), hi, font=fh, fill=col, anchor="ls")
    else:
        lf = font(FONT_MED, 36)
        msg = "Comment your answer below!"
        mw = d.textlength(msg, font=lf)
        d.text((cx - mw / 2, cy + r + 18), msg, font=lf, fill=col)


def option_positions():
    return [(OPT_X, OPT_Y0 + i * OPT_STEP) for i in range(4)]


def render_frames(q, episode, out_path, music_dir=None):
    rng = random.Random(q["id"] * 7919)
    theme = THEMES[q["id"] % len(THEMES)]
    accent = theme[2]
    bilingual = bool(q.get("q_hi"))
    hook = (HOOKS_HI if bilingual else HOOKS)[q["id"] % len(HOOKS)]
    opts = [q["a"]] + list(q["w"])
    opts_hi = ([q["a_hi"]] + list(q["w_hi"])) if bilingual else [None] * 4
    order = list(range(4))
    rng.shuffle(order)
    opts = [opts[i] for i in order]
    opts_hi = [opts_hi[i] for i in order]
    correct = order.index(0)
    labels = "ABCD"

    static = make_static(q, episode, theme, hook)
    normal = [build_option(labels[i], o, "normal", accent, opts_hi[i]) for i, o in enumerate(opts)]
    reveal = [build_option(labels[i], o, "correct" if i == correct else "wrong", accent, opts_hi[i])
              for i, o in enumerate(opts)]
    shadows = [shadow(img) for img in normal]
    fact = make_fact_card(q["f"], theme[0], q.get("f_hi"))
    static_reveal = make_static(q, episode, theme, "")
    fact_sh = shadow(fact)
    pos = option_positions()

    # answer pill
    bf = font(FONT_BOLD, 54)
    btxt = f"ANSWER: {labels[correct]}"
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bw = int(tmp.textlength(btxt, font=bf))
    answer_pill = rounded((bw + 90, 96), 48, GREEN + (255,), outline=(255, 255, 255, 255), width=5)
    ImageDraw.Draw(answer_pill).text((45, 12), btxt, font=bf, fill=(255, 255, 255))

    # audio
    wav_path = out_path + ".wav"
    track = load_music(music_dir, q["id"]) if music_dir else None
    if track is None:
        track = music.background_track(DURATION, seed=q["id"])
    track = music.mix_sfx(track, REVEAL_AT, TICK_FROM)
    music.write_wav(wav_path, track)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n_frames = int(DURATION * FPS)
    for fi in range(n_frames):
        t = fi / FPS
        frame = (static if t < REVEAL_AT else static_reveal).copy()
        if t < REVEAL_AT:
            for i in range(4):
                start = 0.25 + i * 0.18
                p = ease_out_back((t - start) / 0.45)
                if t < start:
                    continue
                x = int(pos[i][0] + (1 - p) * -W)
                frame.alpha_composite(shadows[i], (x - 36, pos[i][1] - 36))
                frame.alpha_composite(normal[i], (x, pos[i][1]))
            draw_timer(frame, t, accent, bilingual)
        else:
            rt = t - REVEAL_AT
            for i in range(4):
                img = reveal[i]
                x, y = pos[i]
                if i == correct:
                    s = 1 + 0.06 * math.sin(min(rt / 0.35, 1) * math.pi) + 0.02 * ease_out(rt / 0.3)
                    img = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
                    x -= (img.width - reveal[i].width) // 2
                    y -= (img.height - reveal[i].height) // 2
                    frame.alpha_composite(shadow(reveal[i]), (pos[i][0] - 36, pos[i][1] - 36))
                frame.alpha_composite(img, (x, y))
            # fact card slides up into the timer's spot
            p = ease_out((rt - 0.35) / 0.5)
            if rt > 0.35:
                fy = int(FACT_Y + (1 - p) * 300)
                frame.alpha_composite(fact_sh, (OPT_X - 36, fy - 36))
                frame.alpha_composite(fact, (OPT_X, fy))
            # green "ANSWER: X" pill pops in over the hook line
            bp = ease_out_back(rt / 0.4)
            pill = answer_pill
            if bp < 1:
                pill = answer_pill.resize((max(1, int(pill.width * bp)), max(1, int(pill.height * bp))), Image.BICUBIC)
            frame.alpha_composite(pill, ((W - pill.width) // 2, HOOK_Y + 32 - pill.height // 2))
            if rt > 2.5:
                d = ImageDraw.Draw(frame)
                cf = font(FONT_BOLD, 40)
                cta = "Follow for 2 new quizzes daily!" if bilingual else "Follow for a new quiz every day!"
                cw = d.textlength(cta, font=cf)
                a = int(255 * ease_out((rt - 2.5) / 0.5))
                d.text((OPT_X + OPT_W / 2 - cw / 2, FACT_Y + fact.height + 16), cta, font=cf, fill=accent + (a,))
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    os.remove(wav_path)
    return {"options": opts, "options_hi": opts_hi, "correct": correct}


def load_music(music_dir, seed):
    files = sorted(glob.glob(os.path.join(music_dir, "*.mp3")) + glob.glob(os.path.join(music_dir, "*.wav"))
                   + glob.glob(os.path.join(music_dir, "*.m4a")))
    if not files:
        return None
    path = random.Random(seed).choice(files)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1",
                          "-ar", str(music.SR), "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    need = int(DURATION * music.SR)
    if len(audio) < need:
        audio = np.tile(audio, need // max(1, len(audio)) + 1)
    audio = audio[:need]
    fade = int(1.0 * music.SR)
    audio[-fade:] *= np.linspace(1, 0, fade)
    peak = max(1e-6, float(np.max(np.abs(audio))))
    return (audio / peak * 0.55).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True, help="question id from questions.json")
    ap.add_argument("--episode", type=int, default=None)
    ap.add_argument("--out", default="out/quiz.mp4")
    args = ap.parse_args()
    qs = json.load(open(os.path.join(ROOT, "questions.json"), encoding="utf-8"))
    q = next(x for x in qs if x["id"] == args.id)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    info = render_frames(q, args.episode or args.id, args.out, os.path.join(ROOT, "assets/music"))
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
