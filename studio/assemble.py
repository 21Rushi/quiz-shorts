#!/usr/bin/env python3
"""Assemble Flow clips (with native voice) into a captioned Short.
Usage: assemble.py spec.json out.mp4 clip1 clip2 clip3 ...
spec: {"tag": "WHAT IF?", "captions": [{"en": "...", "hi": "..."}, ...]}  one caption per clip."""
import json, sys, subprocess, os
sys.path.insert(0, os.path.dirname(__file__))
from engine import text_img, card, F_XB, F_B, F_HI, BRAND
from PIL import Image

spec = json.load(open(sys.argv[1])); out = sys.argv[2]; clips = sys.argv[3:]
tmp = os.path.join(os.path.dirname(out) or '.', '_asm'); os.makedirs(tmp, exist_ok=True)

def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))

# overlay PNGs (1080x1920 transparent)
def layer(draw):
    im = Image.new('RGBA', (1080, 1920)); draw(im); return im

def paste_c(im, src, cx, y):
    im.alpha_composite(src, (int(cx - src.width / 2), int(y)))

def top_layer(im):
    pill = text_img(spec.get('tag', 'WHAT IF?'), F_XB, 50, fill=(20, 20, 30))
    c = card(pill.width + 70, pill.height + 34, (255, 210, 50, 255), 40)
    paste_c(im, c, 540, 200); paste_c(im, pill, 540, 217)
    b = text_img(BRAND, F_B, 34, fill=(255, 255, 255, 200)); im.alpha_composite(b, (60, 55))

lay = [os.path.join(tmp, 'top.png')]; layer(top_layer).save(lay[0])
times = []; t = 0
for i, c in enumerate(clips):
    d = dur(c); times.append((t, t + d)); t += d
    cap = spec['captions'][i]
    def draw(im, cap=cap):
        e = text_img(cap['en'], F_XB, 62, fill=(255, 255, 255), stroke=6, sfill=(0, 0, 0), maxw=930)
        h = text_img(cap['hi'], F_HI, 50, fill=(255, 215, 90), stroke=5, sfill=(0, 0, 0), maxw=930) if cap.get('hi') else None
        y = 1180
        paste_c(im, e, 540, y)
        if h: paste_c(im, h, 540, y + e.height + 22)
    p = os.path.join(tmp, f'cap{i}.png'); layer(draw).save(p); lay.append(p)
T = t
if spec.get('cta'):
    def draw(im):
        c = text_img(spec['cta'], F_XB, 50, fill=(20, 20, 30))
        paste_c(im, card(c.width + 70, c.height + 40, (255, 210, 50, 255), 40), 540, 1560); paste_c(im, c, 540, 1580)
    p = os.path.join(tmp, 'cta.png'); layer(draw).save(p); lay.append(p)

# build ffmpeg
inp = []
for c in clips: inp += ['-i', c]
for l in lay: inp += ['-loop', '1', '-i', l]
n = len(clips); fc = []
for i in range(n):
    fc.append(f'[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1[v{i}];'
              f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]')
fc.append(''.join(f'[v{i}][a{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=1[bv][ba]')
cur = 'bv'; k = n
# top layer whole video (fade in)
fc.append(f'[{k}:v]format=rgba,fade=in:st=0:d=0.4:alpha=1[l0]'); fc.append(f'[{cur}][l0]overlay=0:0:shortest=1[o0]'); cur = 'o0'
for i, (a, b) in enumerate(times):
    li = k + 1 + i
    fc.append(f'[{li}:v]format=rgba,fade=in:st={a + 0.2:.2f}:d=0.3:alpha=1,fade=out:st={b - 0.3:.2f}:d=0.3:alpha=1[c{i}]')
    fc.append(f'[{cur}][c{i}]overlay=0:0:shortest=1[x{i}]'); cur = f'x{i}'
if spec.get('cta'):
    li = k + 1 + n
    fc.append(f'[{li}:v]format=rgba,fade=in:st={T - 3:.2f}:d=0.4:alpha=1[cta]')
    fc.append(f'[{cur}][cta]overlay=0:0:shortest=1:enable=\'gte(t,{T - 3:.2f})\'[xc]'); cur = 'xc'
fc.append(f'[{cur}]fade=out:st={T - 0.6:.2f}:d=0.6,format=yuv420p[vout]')
fc.append(f'[ba]loudnorm=I=-14:TP=-1.5:LRA=11,afade=out:st={T - 0.6:.2f}:d=0.6[aout]')
cmd = ['ffmpeg', '-y', '-loglevel', 'error'] + inp + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
       '-t', f'{T:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-c:a', 'aac', '-b:a', '192k',
       '-ar', '48000', '-movflags', '+faststart', out]
subprocess.run(cmd, check=True)
print('ok', out, round(T, 2))
