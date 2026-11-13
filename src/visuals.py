"""Real photos for Facts Shorts, from Wikimedia Commons (free licences, no API key).

studio/facts_visuals.json maps a date to one list per fact beat (#1, #2, #3):
  {"2026-11-16": [["File:Saturn during Equinox.jpg", "Saturn rings Cassini"], [...], [...]]}
An item starting with "File:" is an exact, already-checked Commons file. Anything else is a
search phrase (the best free-licence photo is picked).

Only public domain, CC0, CC BY and CC BY-SA files are used; the author + licence of every
picture is returned so the video description can credit it.

Usage:
  python src/visuals.py --resolve studio/facts_visuals.json --out preview [--from YYYY-MM-DD]
      -> preview/resolved.json (search phrases replaced by the chosen files) + contact sheets
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "IamRushiShorts/1.0 (https://github.com/21Rushi/quiz-shorts; YouTube @I-mRushi)"
OK_LICENSE = ("public domain", "pd", "cc0", "cc by", "cc-by", "no restrictions")
BAD_WORDS = re.compile(r"\b(map|diagram|chart|logo|icon|graph|plot|schema|schematic|flag|stamp|"
                       r"coat of arms|locator|svg|nude|naked|nudity)\b", re.I)


def _get(url, binary=False, tries=3):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            return data if binary else json.loads(data.decode("utf-8"))
        except Exception as e:  # network hiccup / rate limit - wait and retry
            err = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"fetch failed: {url[:120]} ({err})")


def _clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
    return re.sub(r"\s+", " ", s)[:60]


def _info(page):
    ii = (page.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata") or {}
    lic = (meta.get("LicenseShortName") or {}).get("value", "")
    return {
        "title": page.get("title", ""),
        "url": ii.get("thumburl") or ii.get("url"),
        "w": ii.get("width", 0), "h": ii.get("height", 0), "mime": ii.get("mime", ""),
        "license": _clean(lic),
        "artist": _clean((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons",
        "index": page.get("index", 0),
    }


def _usable(im, strict=True):
    if im["mime"] not in ("image/jpeg", "image/png") or not im["url"]:
        return False
    if not im["license"].lower().startswith(OK_LICENSE):
        return False
    if strict:
        if im["w"] < 900 or im["h"] < 700:
            return False
        ar = im["w"] / max(1, im["h"])
        if ar > 2.6 or ar < 0.45:
            return False
        if BAD_WORDS.search(im["title"]):
            return False
    return True


PROPS = ("&prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=1600"
         "&iiextmetadatafilter=LicenseShortName|Artist&format=json")


def lookup(item, limit=12):
    """Return usable pictures for one item ("File:..." or a search phrase), best first."""
    if item.lower().startswith("file:"):
        data = _get(f"{API}?action=query&titles={urllib.parse.quote(item)}{PROPS}")
        pages = list((data.get("query") or {}).get("pages", {}).values())
        return [im for im in map(_info, pages) if _usable(im, strict=False)]
    q = urllib.parse.quote(f"{item} filetype:bitmap")
    data = _get(f"{API}?action=query&generator=search&gsrnamespace=6&gsrlimit={limit}&gsrsearch={q}{PROPS}")
    pages = list((data.get("query") or {}).get("pages", {}).values())
    ims = sorted(map(_info, pages), key=lambda im: im["index"])
    return [im for im in ims if _usable(im)]


def pick(items, per_beat=2, used=None):
    """Choose up to per_beat different pictures for one fact from its items."""
    used = set() if used is None else used
    out, pools = [], []
    for it in items:
        try:
            pools.append(lookup(it))
        except Exception as e:
            print(f"  ! lookup failed for '{it}': {e}")
            pools.append([])
    rank = 0
    while len(out) < per_beat and any(rank < len(p) for p in pools):
        for p in pools:
            if rank < len(p) and p[rank]["title"] not in used and len(out) < per_beat:
                used.add(p[rank]["title"])
                out.append(p[rank])
        rank += 1
    return out


def download(im, path):
    data = _get(im["url"], binary=True)
    with open(path, "wb") as f:
        f.write(data)
    from PIL import Image
    Image.open(path).verify()   # raises if the download is not a real image
    return path


def fetch_for(date, folder, plan_path, per_beat=2):
    """Download the pictures planned for a date. Returns one list per fact beat:
    [[{"path", "title", "artist", "license"}, ...], ...] - a list is empty if nothing was found."""
    plan = json.load(open(plan_path, encoding="utf-8")).get(date)
    if not plan:
        return []
    os.makedirs(folder, exist_ok=True)
    used, out = set(), []
    for bi, items in enumerate(plan):
        got = []
        for k, im in enumerate(pick(items, per_beat, used)):
            ext = ".png" if im["mime"] == "image/png" else ".jpg"
            try:
                im["path"] = download(im, os.path.join(folder, f"b{bi + 1}_{k + 1}{ext}"))
                got.append(im)
            except Exception as e:
                print(f"  ! download failed for {im['title']}: {e}")
        print(f"  fact {bi + 1}: " + (", ".join(i["title"] for i in got) or "NO PICTURE (text scene will be used)"))
        out.append(got)
    return out


def credits(beats):
    """One short credit line per picture, for the video description."""
    seen, lines = set(), []
    for b in beats:
        for im in b:
            if im["title"] in seen:
                continue
            seen.add(im["title"])
            lines.append(f"{im['artist']} ({im['license']})")
    return list(dict.fromkeys(lines))


def resolve(plan_path, out_dir, start=None, per_beat=2):
    """Turn search phrases into exact files and draw contact sheets so a person can check them."""
    from PIL import Image, ImageDraw
    plan = json.load(open(plan_path, encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)
    resolved, tw, th = {}, 300, 300
    for date in sorted(plan):
        if start and date < start:
            continue
        print(date)
        beats = fetch_for(date, os.path.join(out_dir, "img", date), plan_path, per_beat)
        resolved[date] = [[{"title": im["title"], "artist": im["artist"], "license": im["license"]} for im in b] for b in beats]
        sheet = Image.new("RGB", (tw * per_beat * 3, th + 40), (20, 20, 30))
        d = ImageDraw.Draw(sheet)
        d.text((8, 4), f"{date}  " + " | ".join("/".join(i)[:50] for i in plan[date]), fill=(255, 255, 255))
        for bi, b in enumerate(beats):
            for k, im in enumerate(b):
                t = Image.open(im["path"]).convert("RGB")
                t.thumbnail((tw - 8, th - 8))
                sheet.paste(t, (bi * per_beat * tw + k * tw + 4, 40))
        sheet.save(os.path.join(out_dir, f"sheet_{date}.jpg"), quality=80)
    json.dump(resolved, open(os.path.join(out_dir, "resolved.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    missing = [f"{d} fact {i + 1}" for d, bs in resolved.items() for i, b in enumerate(bs) if not b]
    print("Missing pictures:", missing or "none")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", required=True)
    ap.add_argument("--out", default="preview")
    ap.add_argument("--from", dest="start", default=None)
    a = ap.parse_args()
    resolve(a.resolve, a.out, a.start)
    sys.exit(0)
