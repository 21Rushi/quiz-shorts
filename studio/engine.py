#!/usr/bin/env python3
"""Animated Shorts engine. Usage: engine.py spec.json out.mp4
Spec type 'quiz' or 'story' (see examples in specs/)."""
import json, sys, math, random, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FD = os.path.expanduser('~/fonts/package')
F_XB = f'{FD}/800ExtraBold/Montserrat_800ExtraBold.ttf'
F_B = f'{FD}/700Bold/Montserrat_700Bold.ttf'
F_HI = f'{FD}/700Bold/NotoSansDevanagari_700Bold.ttf'
BRAND = '@I-mRushi'

_fonts = {}
def font(p, s):
    k = (p, s)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(p, s, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eob(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def prog(t, a, d): return clamp((t - a) / d)
def lerp(a, b, x): return a + (b - a) * x
def lerpc(c1, c2, x): return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))

_tc = {}
def text_img(text, path, size, fill=(255, 255, 255), stroke=0, sfill=(0, 0, 0), maxw=940, spacing=12, align='center'):
    k = (text, path, size, fill, stroke, sfill, maxw, align)
    if k in _tc: return _tc[k]
    f = font(path, size)
    d = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split(' '):
            tst = (cur + ' ' + w).strip()
            if not cur or d.textlength(tst, font=f) <= maxw: cur = tst
            else: lines.append(cur); cur = w
        lines.append(cur)
    txt = '\n'.join(lines)
    bb = d.multiline_textbbox((0, 0), txt, font=f, stroke_width=stroke, spacing=spacing, align=align)
    im = Image.new('RGBA', (int(bb[2] - bb[0]) + 6, int(bb[3] - bb[1]) + 6))
    ImageDraw.Draw(im).multiline_text((int(-bb[0]) + 3, int(-bb[1]) + 3), txt, font=f, fill=fill, stroke_width=stroke,
                                      stroke_fill=sfill, spacing=spacing, align=align)
    _tc[k] = im
    return im

_cc = {}
def card(w, h, color, r=36, outline=None, ow=0):
    k = (w, h, color, r, outline, ow)
    if k not in _cc:
        im = Image.new('RGBA', (w, h))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=color, outline=outline, width=ow)
        _cc[k] = im
    return _cc[k]

_gc = {}
def glow(r, color):
    k = (r, color)
    if k not in _gc:
        y, x = np.mgrid[-r:r, -r:r]
        a = np.exp(-(x ** 2 + y ** 2) / (2 * (r / 2.6) ** 2))
        arr = np.zeros((2 * r, 2 * r, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = (a * 255).astype(np.uint8)
        _gc[k] = Image.fromarray(arr, 'RGBA')
    return _gc[k]

def put(cv, im, cx, cy, alpha=1.0, scale=1.0, top=False):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.995:
        a = np.asarray(im.getchannel('A'), np.float32) * alpha
        im = im.copy(); im.putalpha(Image.fromarray(a.astype(np.uint8), 'L'))
    x = int(cx - im.width / 2); y = int(cy if top else cy - im.height / 2)
    cv.paste(im, (x, y), im)

# ---------------- background ----------------
class Background:
    def __init__(self, c1, c2, seed=7, nstars=160):
        y = np.linspace(0, 1, H)[:, None, None]
        arr = np.array(c1, np.float32) * (1 - y) + np.array(c2, np.float32) * y
        arr = np.broadcast_to(arr, (H, W, 3)).copy()
        yy, xx = np.mgrid[0:H, 0:W]
        v = 1 - 0.45 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2
        arr *= v[..., None]
        self.base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        rnd = random.Random(seed)
        self.stars = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.2, 3.6), rnd.uniform(0, 6.28),
                       rnd.uniform(8, 40)) for _ in range(nstars)]

    def frame(self, t, accent=None):
        cv = self.base.copy()
        d = ImageDraw.Draw(cv)
        for x, y, r, ph, sp in self.stars:
            yy = (y + t * sp) % H
            b = int(140 + 115 * (0.5 + 0.5 * math.sin(ph + t * 2.2)))
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(b, b, min(255, b + 20)))
        if accent:
            put(cv, glow(520, accent), W / 2 + 160 * math.sin(t * 0.35), 700 + 120 * math.cos(t * 0.27), 0.35)
        return cv

# ---------------- planet ----------------
_pc = {}
class Planet:
    def __init__(self, r, base, land, seed=3):
        self.r = r; rnd = random.Random(seed)
        tw = r * 4
        tex = Image.new('RGB', (tw, 2 * r), base); d = ImageDraw.Draw(tex)
        for _ in range(55):
            x = rnd.uniform(0, tw); y = rnd.uniform(0.12, 0.88) * 2 * r; rr = rnd.uniform(r / 12, r / 4)
            d.ellipse((x - rr, y - rr * 0.65, x + rr, y + rr * 0.65), fill=land)
        tex = tex.filter(ImageFilter.GaussianBlur(4))
        self.tex = Image.new('RGB', (tw * 2, 2 * r)); self.tex.paste(tex, (0, 0)); self.tex.paste(tex, (tw, 0))
        self.tw = tw
        m = Image.new('L', (2 * r, 2 * r)); ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        self.mask = m
        y, x = np.mgrid[-r:r, -r:r] / r
        z = np.sqrt(np.clip(1 - x ** 2 - y ** 2, 0, 1))
        light = np.clip(-0.55 * x - 0.45 * y + 0.7 * z, 0, 1)
        a = (1 - light) * 215
        inside = (x ** 2 + y ** 2) <= 1
        sh = np.zeros((2 * r, 2 * r, 4), np.uint8)
        sh[..., 3] = np.where(inside, a, 0).astype(np.uint8)
        self.shade = Image.fromarray(sh, 'RGBA')

    def img(self, offset, overlay=None):
        o = int(offset) % self.tw
        out = self.tex.crop((o, 0, o + 2 * self.r, 2 * self.r)).convert('RGBA')
        if overlay: overlay(out)
        out.putalpha(self.mask)
        out.alpha_composite(self.shade)
        return out

def get_planet(key, r, base, land):
    k = (key, r, base, land)
    if k not in _pc: _pc[k] = Planet(r, base, land)
    return _pc[k]

# ---------------- scenes (story) ----------------
def sc_planet(cv, tl, dur, p, T):
    r = p.get('r', 300); cy = p.get('y', 720)
    pl = get_planet('e', r, tuple(p.get('base', (40, 110, 200))), tuple(p.get('land', (70, 160, 90))))
    spin = p.get('spin', 120); stop = p.get('stop_at')
    off = spin * tl if stop is None else (spin * tl if tl < stop else spin * stop + spin * 0.6 * (1 - math.exp(-(tl - stop) * 3)))
    put(cv, glow(int(r * 1.5), tuple(p.get('glow', (90, 160, 255)))), W / 2, cy, 0.55)
    s = eob(prog(tl, 0, 0.6))
    put(cv, pl.img(off), W / 2, cy, 1, s)
    if stop is not None and tl >= stop:
        k = prog(tl, stop, 0.4)
        d = ImageDraw.Draw(cv)
        sx = W / 2; sy = cy
        rr = r * 0.32 * eob(k)
        d.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), fill=(220, 40, 50))
        txt = text_img('STOP', F_XB, int(max(8, 64 * eob(k))))
        put(cv, txt, sx, sy)

def sc_counter(cv, tl, dur, p, T):
    cy = p.get('y', 700); a, b = p['from'], p['to']
    v = lerp(a, b, eo(prog(tl, 0.2, dur * 0.55)))
    d = ImageDraw.Draw(cv)
    R = 300; bbox = (W / 2 - R, cy - R, W / 2 + R, cy + R)
    d.arc(bbox, 135, 405, fill=(60, 70, 110), width=34)
    end = 135 + 270 * (v - a) / max(1e-6, (b - a))
    d.arc(bbox, 135, end, fill=tuple(p.get('color', (255, 200, 40))), width=34)
    num = text_img(f"{int(v):,}", F_XB, 150, fill=(255, 255, 255))
    put(cv, num, W / 2, cy - 20)
    put(cv, text_img(p.get('unit', ''), F_B, 64, fill=tuple(p.get('color', (255, 200, 40)))), W / 2, cy + 110)

def sc_streaks(cv, tl, dur, p, T):
    rnd = random.Random(11); d = ImageDraw.Draw(cv)
    pl = get_planet('e', 220, (40, 110, 200), (70, 160, 90))
    put(cv, pl.img(0), W / 2, 980)
    for i in range(36):
        y = rnd.uniform(380, 900); L = rnd.uniform(120, 420); sp = rnd.uniform(900, 1900)
        x = (rnd.uniform(0, W + L) + tl * sp) % (W + L) - L
        a = int(rnd.uniform(90, 230))
        d.line((x, y, x + L, y), fill=(a, a, 255), width=int(rnd.uniform(3, 8)))
    cols = [(255, 180, 60), (250, 90, 90), (120, 220, 140), (240, 240, 240)]
    for i in range(9):
        y = rnd.uniform(420, 860); sp = rnd.uniform(700, 1300); sz = rnd.uniform(28, 60)
        x = (rnd.uniform(0, W) + tl * sp) % (W + 200) - 100
        ang = tl * rnd.uniform(200, 600)
        sq = Image.new('RGBA', (int(sz), int(sz))); ImageDraw.Draw(sq).rounded_rectangle((0, 0, sz - 1, sz - 1), 6, fill=cols[i % 4])
        sq = sq.rotate(ang, expand=True)
        cv.paste(sq, (int(x), int(y)), sq)
    arrow = text_img('EAST  >>>', F_XB, 70, fill=(255, 220, 80))
    put(cv, arrow, W / 2 + 30 * math.sin(tl * 8), 330)

def sc_oceans(cv, tl, dur, p, T):
    r = 300; cy = 720
    pl = get_planet('land', r, (150, 120, 70), (110, 150, 80))
    k = eo(prog(tl, 0.3, dur * 0.7))
    def ov(im):
        d = ImageDraw.Draw(im); h = int(r * (0.25 + 0.55 * k))
        d.ellipse((-r * 0.5, -h, 2.5 * r, h), fill=(40, 110, 220))
        d.ellipse((-r * 0.5, 2 * r - h, 2.5 * r, 2 * r + h), fill=(40, 110, 220))
    put(cv, glow(int(r * 1.5), (90, 160, 255)), W / 2, cy, 0.5)
    put(cv, pl.img(0, ov), W / 2, cy)
    a = text_img('^', F_XB, 120, fill=(120, 200, 255)); b = text_img('v', F_XB, 110, fill=(120, 200, 255))
    bob = 20 * math.sin(tl * 6)
    put(cv, text_img('NORTH POLE', F_B, 44, fill=(170, 220, 255)), W / 2, cy - r - 120)
    put(cv, a, W / 2, cy - r - 50 - bob); put(cv, b, W / 2, cy + r + 50 + bob)
    put(cv, text_img('SOUTH POLE', F_B, 44, fill=(170, 220, 255)), W / 2, cy + r + 125)

def sc_daynight(cv, tl, dur, p, T):
    cy = 720; R = 300; d = ImageDraw.Draw(cv)
    s = eob(prog(tl, 0, 0.6))
    im = Image.new('RGBA', (2 * R, 2 * R)); dd = ImageDraw.Draw(im)
    dd.pieslice((0, 0, 2 * R - 1, 2 * R - 1), 90, 270, fill=(255, 196, 60))
    dd.pieslice((0, 0, 2 * R - 1, 2 * R - 1), 270, 450, fill=(20, 28, 70))
    dd.ellipse((R * 0.38, R * 0.62, R * 0.38 + R * 0.5, R * 0.62 + R * 0.5), fill=(255, 245, 190))
    dd.ellipse((R * 1.25, R * 0.6, R * 1.25 + R * 0.45, R * 0.6 + R * 0.45), fill=(230, 230, 245))
    dd.ellipse((R * 1.38, R * 0.55, R * 1.38 + R * 0.45, R * 0.55 + R * 0.45), fill=(20, 28, 70))
    put(cv, glow(int(R * 1.4), (255, 190, 80)), W / 2 - 120, cy, 0.4)
    put(cv, im, W / 2, cy, 1, s)
    put(cv, text_img('6 MONTHS\nDAY', F_XB, 46, fill=(255, 220, 120)), W / 2 - 200, cy + R + 80, eo(prog(tl, 0.6, 0.4)))
    put(cv, text_img('6 MONTHS\nNIGHT', F_XB, 46, fill=(170, 190, 255)), W / 2 + 200, cy + R + 80, eo(prog(tl, 0.8, 0.4)))

def sc_clock(cv, tl, dur, p, T):
    cy = 720; R = 270; d = ImageDraw.Draw(cv)
    d.ellipse((W / 2 - R, cy - R, W / 2 + R, cy + R), fill=(245, 245, 255), outline=(255, 200, 40), width=18)
    for i in range(12):
        a = i * math.pi / 6; x1 = W / 2 + math.sin(a) * R * 0.82; y1 = cy - math.cos(a) * R * 0.82
        x2 = W / 2 + math.sin(a) * R * 0.92; y2 = cy - math.cos(a) * R * 0.92
        d.line((x1, y1, x2, y2), fill=(30, 30, 60), width=10)
    sp = p.get('speed', 2.0)
    for L, w, f in ((0.5, 18, sp / 12), (0.78, 10, sp)):
        a = tl * f * 2 * math.pi
        d.line((W / 2, cy, W / 2 + math.sin(a) * R * L, cy - math.cos(a) * R * L), fill=(20, 20, 50), width=w)
    d.ellipse((W / 2 - 18, cy - 18, W / 2 + 18, cy + 18), fill=(255, 80, 80))
    if p.get('label'):
        put(cv, text_img(p['label'], F_XB, 60, fill=(255, 220, 80)), W / 2, cy + R + 80)

def sc_big(cv, tl, dur, p, T):
    put(cv, glow(420, tuple(p.get('glow', (255, 120, 60)))), W / 2, 720, 0.6)
    put(cv, text_img(p['text'], F_XB, p.get('size', 220), fill=tuple(p.get('color', (255, 220, 80))), stroke=8),
        W / 2, 720, 1, eob(prog(tl, 0, 0.5)) * (1 + 0.03 * math.sin(tl * 5)))

SCENES = dict(planet=sc_planet, counter=sc_counter, streaks=sc_streaks, oceans=sc_oceans,
              daynight=sc_daynight, clock=sc_clock, big=sc_big)

def caption(cv, t, a, b, en, hi, y=1230):
    k_in = eo(prog(t, a, 0.45)); k_out = 1 - prog(t, b - 0.35, 0.35)
    al = min(k_in, k_out)
    if al <= 0: return
    dy = (1 - k_in) * 60
    e = text_img(en, F_XB, 66, fill=(255, 255, 255), stroke=5, sfill=(10, 10, 30), maxw=930)
    put(cv, e, W / 2, y + dy, al, top=True)
    if hi:
        h = text_img(hi, F_HI, 50, fill=(255, 215, 90), stroke=4, sfill=(10, 10, 30), maxw=930)
        put(cv, h, W / 2, y + e.height + 26 + dy, al, top=True)

def brand(cv):
    put(cv, text_img(BRAND, F_B, 34, fill=(255, 255, 255)), 170, 70, 0.75)

# ---------------- renderers ----------------
def render_story(spec, t, bg):
    T = spec['duration']
    cv = bg.frame(t, tuple(spec.get('accent', (120, 60, 220))))
    pill = text_img(spec.get('tag', 'WHAT IF?'), F_XB, 50, fill=(20, 20, 30))
    c = card(pill.width + 70, pill.height + 34, (255, 210, 50), 40)
    put(cv, c, W / 2, 230, 1, eob(prog(t, 0, 0.5))); put(cv, pill, W / 2, 230, 1, eob(prog(t, 0, 0.5)))
    for bt in spec['beats']:
        a, b = bt['start'], bt['end']
        if a - 0.01 <= t < b + 0.01:
            tl = t - a
            fade = min(eo(prog(t, a, 0.35)), 1 - prog(t, b - 0.3, 0.3)) if bt is not spec['beats'][-1] else eo(prog(t, a, 0.35))
            m = cv.copy()
            SCENES[bt['scene']['type']](m, tl, b - a, bt['scene'], T)
            cv = Image.blend(cv, m, fade) if fade < 0.995 else m
            caption(cv, t, a, b if bt is not spec['beats'][-1] else T + 1, bt['en'], bt.get('hi'))
    brand(cv)
    return cv

def render_quiz(spec, t, bg):
    T = spec.get('duration', 30); R = spec.get('reveal', 25)
    cv = bg.frame(t, tuple(spec.get('accent', (40, 120, 255))))
    s = eob(prog(t, 0, 0.5))
    pill = text_img('QUIZ TIME', F_XB, 58, fill=(20, 20, 30))
    c = card(pill.width + 80, pill.height + 36, (255, 210, 50), 44)
    put(cv, c, W / 2, 230, 1, s); put(cv, pill, W / 2, 230, 1, s)
    hook = text_img(spec.get('hook', 'Only 1% get this right!'), F_B, 40, fill=(255, 230, 150))
    put(cv, hook, W / 2, 315, 1 - prog(t, 3.5, 0.5))
    # question card
    qe = text_img(spec['q_en'], F_XB, 58, fill=(20, 24, 50), maxw=860)
    qh = text_img(spec.get('q_hi', ''), F_HI, 44, fill=(90, 60, 160), maxw=860) if spec.get('q_hi') else None
    ch = qe.height + (qh.height + 24 if qh else 0) + 80
    k = eo(prog(t, 0.3, 0.6)); y0 = 380 + (1 - k) * -80
    put(cv, card(960, ch, (255, 255, 255), 40), W / 2, y0, k, top=True)
    put(cv, qe, W / 2, y0 + 40, k, top=True)
    if qh: put(cv, qh, W / 2, y0 + 40 + qe.height + 24, k, top=True)
    oy = y0 + ch + 60 if k > 0 else 800
    oy = 380 + ch + 60
    letters = 'ABCD'
    for i, op in enumerate(spec['options']):
        st = 1.2 + i * 0.3
        kk = eo(prog(t, st, 0.45)); x = W / 2 + (1 - kk) * -700
        y = oy + i * 145
        correct = i == spec['answer']
        rv = prog(t, R, 0.35)
        col = (255, 255, 255, 38); al = kk
        sc = 1.0
        if t >= R:
            if correct: col = (29, 185, 84, 255); sc = 1 + 0.06 * math.sin(min(1, (t - R) / 0.5) * math.pi)
            else: al = kk * (1 - 0.65 * rv)
        cd = card(900, 120, col, 30, outline=(255, 255, 255, 90), ow=3)
        put(cv, cd, x, y + 60, al, sc)
        circ = Image.new('RGBA', (80, 80)); ImageDraw.Draw(circ).ellipse((0, 0, 79, 79), fill=(255, 210, 50) if not (t >= R and correct) else (255, 255, 255))
        put(cv, circ, x - 380, y + 60, al, sc)
        put(cv, text_img(letters[i], F_XB, 46, fill=(20, 20, 30)), x - 380, y + 60, al, sc)
        put(cv, text_img(op['en'], F_XB, 54, fill=(255, 255, 255), maxw=520), x - 320 + text_img(op['en'], F_XB, 54, maxw=520).width / 2, y + 60, al, sc)
        if op.get('hi'):
            hi = text_img(op['hi'], F_HI, 42, fill=(255, 225, 140))
            put(cv, hi, x + 410 - hi.width / 2, y + 60, al, sc)
    # timer
    ty = 1470
    if 3 <= t < R:
        frac = clamp((R - t) / (R - 3)); d = ImageDraw.Draw(cv); Rr = 120
        col = lerpc((240, 60, 60), (60, 220, 120), frac) if frac < 0.5 else lerpc((60, 220, 120), (60, 220, 120), 1)
        if frac < 0.5: col = lerpc((240, 60, 60), (255, 200, 40), frac * 2)
        else: col = lerpc((255, 200, 40), (60, 220, 120), (frac - 0.5) * 2)
        d.ellipse((W / 2 - Rr, ty - Rr, W / 2 + Rr, ty + Rr), fill=(15, 18, 40))
        d.arc((W / 2 - Rr, ty - Rr, W / 2 + Rr, ty + Rr), -90, -90 + 360 * frac, fill=col, width=20)
        n = max(1, math.ceil(R - t))
        pulse = 1 + 0.12 * max(0, 1 - ((t % 1) / 0.25)) if n <= 5 else 1
        put(cv, text_img(str(n), F_XB, 110, fill=(255, 255, 255)), W / 2, ty, 1, pulse)
        put(cv, text_img('Comment your answer!', F_B, 44, fill=(255, 255, 255), stroke=3, sfill=(10, 10, 30)), W / 2, ty + 175)
    if t >= R:
        k = eo(prog(t, R + 0.3, 0.5))
        fe = text_img(spec['fact_en'], F_B, 46, fill=(255, 255, 255), maxw=860)
        fh = text_img(spec.get('fact_hi', ''), F_HI, 40, fill=(255, 225, 140), maxw=860) if spec.get('fact_hi') else None
        h = fe.height + (fh.height + 20 if fh else 0) + 70
        top = 1345 + (1 - k) * 60
        put(cv, card(960, h, (10, 14, 40, 225), 34, outline=(255, 210, 50), ow=4), W / 2, top, k, top=True)
        put(cv, fe, W / 2, top + 35, k, top=True)
        if fh: put(cv, fh, W / 2, top + 35 + fe.height + 20, k, top=True)
        k2 = eob(prog(t, R + 1.6, 0.5))
        cta = text_img('Follow for a new quiz daily!', F_XB, 46, fill=(20, 20, 30))
        p = 1 + 0.04 * math.sin(t * 6)
        put(cv, card(cta.width + 70, cta.height + 40, (255, 210, 50), 40), W / 2, top + h + 75, 1, k2 * p)
        put(cv, cta, W / 2, top + h + 75, 1, k2 * p)
    brand(cv)
    return cv

# ---------------- audio ----------------
SR = 44100
def env(n, a, r):
    e = np.ones(n); na = int(a * SR); nr = int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def add(buf, t0, sig):
    i = int(t0 * SR)
    if i >= len(buf): return
    sig = sig[:len(buf) - i]; buf[i:i + len(sig)] += sig
def tone(f, d, decay=None, amp=1.0):
    t = np.arange(int(d * SR)) / SR
    s = np.sin(2 * np.pi * f * t) * amp
    return s * (np.exp(-t * decay) if decay else 1)

def make_audio(spec, path):
    T = spec['duration']; n = int(T * SR); buf = np.zeros(n)
    rnd = np.random.default_rng(5)
    prog_ = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66], [164.81, 207.65, 246.94]]
    if spec['type'] == 'story':
        prog_ = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [130.81, 164.81, 196.0], [110.0, 138.59, 164.81]]
    for i in range(int(T // 4) + 1):
        ch = prog_[i % 4]; d = min(4.6, T - i * 4)
        if d <= 0: break
        for f in ch:
            t = np.arange(int(d * SR)) / SR
            s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t) + 0.15 * np.sin(2 * np.pi * f * 0.5 * t))
            add(buf, i * 4, s * env(len(t), 0.6, 1.0) * 0.045)
        # arpeggio
        for j in range(8):
            f = ch[j % 3] * (2 if j % 4 < 2 else 4)
            add(buf, i * 4 + j * 0.5, tone(f, 0.45, 7, 0.035))
    # kick pulse
    for k in np.arange(0, T, 0.5):
        t = np.arange(int(0.18 * SR)) / SR
        f = 120 * np.exp(-t * 18) + 45
        add(buf, k, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * (0.22 if k % 1 == 0 else 0.1))
    def whoosh(t0):
        d = 0.6; m = int(d * SR); no = rnd.standard_normal(m)
        no = np.convolve(no, np.ones(30) / 30, 'same')
        e = np.sin(np.linspace(0, np.pi, m)) ** 2
        add(buf, t0, no * e * 0.5)
    def pop(t0):
        t = np.arange(int(0.09 * SR)) / SR; f = np.linspace(500, 1100, len(t))
        add(buf, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.3)
    def ding(t0):
        add(buf, t0, tone(1318.5, 1.6, 2.5, 0.35) + tone(1975.5, 1.6, 3, 0.2)); add(buf, t0, tone(2637, 1.0, 4, 0.08))
    def tick(t0, loud=0.18):
        add(buf, t0, tone(2000, 0.035, 90, loud)); add(buf, t0, tone(3200, 0.02, 120, loud * 0.5))
    def boom(t0):
        t = np.arange(int(1.0 * SR)) / SR
        add(buf, t0, np.sin(2 * np.pi * (55 * t + 20 * (1 - np.exp(-t * 5)) / 5)) * np.exp(-t * 3.5) * 0.6)
    if spec['type'] == 'quiz':
        R = spec.get('reveal', 25); boom(0); whoosh(0.25)
        for i in range(4): pop(1.2 + i * 0.3)
        for s in range(3, int(R)): tick(s, 0.26 if R - s <= 5 else 0.16)
        whoosh(R - 0.3); ding(R); pop(R + 1.6)
    else:
        boom(0)
        for bt in spec['beats'][1:]: whoosh(bt['start'] - 0.3)
    buf *= np.minimum(1, (T - np.arange(n) / SR) / 1.5)  # fade out
    buf /= max(1e-6, np.abs(buf).max()) / 0.85
    st = (np.stack([buf, buf], 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())

def main(specp, out):
    spec = json.load(open(specp))
    T = spec['duration']
    th = spec.get('theme', [(12, 10, 40), (40, 10, 70)])
    bg = Background(tuple(th[0]), tuple(th[1]))
    wav = out + '.wav'; make_audio(spec, wav)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out],
                         stdin=subprocess.PIPE)
    rf = render_quiz if spec['type'] == 'quiz' else render_story
    for i in range(int(T * FPS)):
        t = i / FPS
        p.stdin.write(rf(spec, t, bg).tobytes())
    p.stdin.close(); p.wait(); os.remove(wav)
    print('ok', out)

if __name__ == '__main__':
    if len(sys.argv) > 3:  # preview frames: engine.py spec.json outprefix t1 t2 ...
        spec = json.load(open(sys.argv[1])); th = spec.get('theme', [(12, 10, 40), (40, 10, 70)])
        bg = Background(tuple(th[0]), tuple(th[1]))
        rf = render_quiz if spec['type'] == 'quiz' else render_story
        for ts in sys.argv[3:]:
            rf(spec, float(ts), bg).resize((360, 640)).save(f'{sys.argv[2]}_{ts}.png')
    else:
        main(sys.argv[1], sys.argv[2])
