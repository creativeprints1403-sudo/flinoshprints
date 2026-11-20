"""Make 9:16 Instagram Reels (1080x1920 MP4) from product photos.

Reels are described in social/reels.json. Each scene is a photo (a site path
or an https URL, e.g. an Amazon listing photo) on a soft background with a
headline, shown with a slow zoom, then an end card saying how to order.
Needs Pillow and ffmpeg.

    python3 scripts/make_reel.py            # build every reel not built yet
    python3 scripts/make_reel.py NAME ...   # (re)build these reels
"""
import io
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_post_cards import watermark

ROOT = Path(__file__).resolve().parent.parent
REELS = ROOT / "social" / "reels.json"
OUT = ROOT / "assets" / "reels"
W, H, FPS = 1080, 1920, 30
SCENE_S, END_S, FADE_S = 2.8, 3.6, 0.5
INK, PINK, GOLD = (52, 36, 24), (224, 26, 130), (176, 132, 52)
BGS = [(250, 244, 233), (240, 234, 248), (251, 238, 242), (236, 245, 240), (246, 240, 232)]


def first(*paths):
    return next((p for p in paths if Path(p).exists()), paths[-1])


SERIF = first("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
SANS = first("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SANS_BOLD = first("/usr/share/fonts/opentype/inter/Inter-Bold.otf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def load(src, crop=None):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            im = Image.open(io.BytesIO(r.read()))
    else:
        im = Image.open(ROOT / src)
    im = im.convert("RGB")
    return im.crop(tuple(crop)) if crop else im


def fit(draw, text, path, size, width=980):
    while draw.textlength(text, font=font(path, size)) > width and size > 30:
        size -= 2
    return font(path, size)


def centred(draw, y, text, f, fill):
    draw.text(((W - draw.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def footer(im, d, brand):
    if brand.get("logo", "assets/logo-mark.webp"):
        logo = Image.open(ROOT / brand.get("logo", "assets/logo-mark.webp")).convert("RGBA")
        logo.thumbnail((84, 84))
        im.paste(logo, (W // 2 - 230, 1740), logo)
        d.text((W // 2 - 130, 1752), brand.get("footer", "flinoshprints"), font=font(SANS_BOLD, 46),
               fill=tuple(brand.get("ink", INK)))
    else:
        centred(d, 1752, brand["footer"], font(SANS_BOLD, 46), tuple(brand.get("ink", INK)))


def scene_frame(photo, headline, subline, bg, zoom, brand=None, overlay=None, big=None):
    brand = brand or {}
    ink, gold = tuple(brand.get("ink", INK)), tuple(brand.get("accent", GOLD))
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    if big:  # a text-only scene: big lines in the middle, gently growing
        y = 760 - 70 * len(big)
        for i, line in enumerate(big):
            f = fit(d, line, SANS_BOLD, int(120 * (0.97 + 0.03 * zoom / 1.06)))
            centred(d, y, line, f, gold if i == len(big) - 1 else ink)
            y += 150
        if subline:
            centred(d, y + 40, subline, fit(d, subline, SANS, 46), ink)
        footer(im, d, brand)
        return im
    centred(d, 210, headline, fit(d, headline, SERIF, 76), ink)
    if subline:
        centred(d, 320, subline, fit(d, subline, SANS, 44), gold)
    scale = min(940 / photo.width, 1180 / photo.height) * zoom
    ph = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    x, y = (W - ph.width) // 2, 460 + (1200 - ph.height) // 2
    im.paste(ph, (x, y))
    if brand.get("logo", "assets/logo-mark.webp"):  # Flinosh photos get the tiled watermark
        wm = watermark(ph.size)
        im.paste(wm, (x, y), wm)
    if overlay:  # an ad-style caption and price on the photo
        f = fit(d, overlay["text"], SANS_BOLD, 62, ph.width - 80)
        tw = d.textlength(overlay["text"], font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 30, y + ph.height - 190, W / 2 + tw / 2 + 30, y + ph.height - 100),
                            20, fill=(30, 22, 14))
        centred(d, y + ph.height - 178, overlay["text"], f, "white")
        if overlay.get("price"):
            pf = font(SANS_BOLD, 58)
            pw = d.textlength(overlay["price"], font=pf)
            d.rounded_rectangle((x + 30, y + 30, x + 80 + pw, y + 120), 18, fill=(255, 204, 0))
            d.text((x + 55, y + 42), overlay["price"], font=pf, fill=(30, 22, 14))
    footer(im, d, brand)
    return im


def end_frame(title, lines, foot, brand=None):
    brand = brand or {}
    ink, gold = tuple(brand.get("ink", INK)), tuple(brand.get("accent", GOLD))
    pink = tuple(brand.get("button", PINK))
    im = Image.new("RGB", (W, H), tuple(brand.get("end_bg", (252, 247, 240))))
    d = ImageDraw.Draw(im)
    if brand.get("logo", "assets/logo-mark.webp"):
        logo = Image.open(ROOT / brand.get("logo", "assets/logo-mark.webp")).convert("RGBA")
        logo.thumbnail((220, 220))
        im.paste(logo, ((W - logo.width) // 2, 430), logo)
    else:
        centred(d, 520, brand.get("wordmark", ""), font(SANS_BOLD, 110), ink)
    centred(d, 760, title, fit(d, title, SERIF, 78), ink)
    y = 920
    for i, line in enumerate(lines):
        f = font(SANS_BOLD, 64 if i == 0 else 52)
        tw = d.textlength(line, font=f)
        if i == 0:
            d.rounded_rectangle(((W - tw) / 2 - 50, y - 24, (W + tw) / 2 + 50, y + 100), 62, fill=pink)
            d.text(((W - tw) / 2, y), line, font=f, fill="white")
        else:
            d.text(((W - tw) / 2, y + 30), line, font=f, fill=ink)
        y += 170
    centred(d, y + 60, foot, fit(d, foot, SANS, 40), gold)
    return im


HOOK_SCENE_S, HOOK_END_S = 1.4, 1.6


def caption(d, y, text, f, fill, box):
    tw = d.textlength(text, font=f)
    d.rounded_rectangle(((W - tw) / 2 - 36, y - 18, (W + tw) / 2 + 36, y + f.size + 26), 26, fill=box)
    centred(d, y, text, f, fill)


def hook_frame(photo, bg, zoom, top, brand, order=None):
    """Hook-first look: the product fills the frame and moves from frame 1,
    with bold text on top. Without photo, a plain card."""
    ink, pink = tuple(brand.get("ink", INK)), tuple(brand.get("button", PINK))
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    if photo:
        scale = min(1040 / photo.width, 1340 / photo.height) * zoom
        ph = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
        x, y = (W - ph.width) // 2, 470 + (1240 - ph.height) // 2
        im.paste(ph, (x, y))
        if brand.get("logo", "assets/logo-mark.webp"):
            wm = watermark(ph.size)
            im.paste(wm, (x, y), wm)
    y = 170
    for i, line in enumerate(top):
        f = fit(d, line, SANS_BOLD, 104 if i == 0 else 66, 940)
        if i == 0:
            caption(d, y, line, f, "white", pink)
        else:
            caption(d, y, line, f, ink, (255, 255, 255))
        y += f.size + 70
    if order:
        f = fit(d, order[0], SANS_BOLD, 64, 900)
        caption(d, 1500, order[0], f, "white", (30, 22, 14))
        if len(order) > 1:
            f2 = fit(d, order[1], SANS_BOLD, 48, 900)
            caption(d, 1630, order[1], f2, ink, (255, 255, 255))
    footer(im, d, brand)
    return im


def beat_wav(path, seconds):
    """A soft 118 bpm kick and pad, stdlib only, so the reel isn't silent."""
    import math, struct, wave
    sr, step = 22050, 60 / 118
    n = int(sr * seconds)
    out = [0.0] * n
    for k in range(int(seconds / step) + 1):
        s0 = int(k * step * sr)
        for j in range(min(int(0.22 * sr), n - s0)):
            t = j / sr
            out[s0 + j] += 0.8 * math.sin(2 * math.pi * (55 + 90 * math.exp(-t * 30)) * t) * math.exp(-t * 9)
    for i in range(n):
        t = i / sr
        out[i] += 0.05 * (math.sin(2 * math.pi * 220 * t) + math.sin(2 * math.pi * 277.2 * t)
                          + math.sin(2 * math.pi * 329.6 * t)) * min(1, t * 3)
    peak = max(abs(v) for v in out) or 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(v / peak * 0.7 * 32767)) for v in out))


def build_hook(reel):
    """About 7 seconds: hook on a moving product shot in the first second,
    quick cuts, and an ending that matches the opening so it loops."""
    brand = reel.get("brand", {})
    scenes = reel["scenes"][:4]
    photos = [load(s["image"], s.get("crop")) if s.get("image") else None for s in scenes]
    end = reel.get("end", {})
    order = end.get("lines", ["WhatsApp 95793 06816", "flinoshprints.com"])
    n = int(HOOK_SCENE_S * FPS)
    out = OUT / f"{reel['name']}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        for i, (s, photo) in enumerate(zip(scenes, photos)):
            bg = tuple(s.get("bg") or brand.get("bg") or BGS[i % len(BGS)])
            top = reel["hook"] if i == 0 else [s.get("headline", ""), s.get("subline", "")]
            top = [t for t in top if t]
            for j in range(n):
                t = j / FPS
                # first scene punches in from 1.15 to 1.0, the rest drift in slowly
                zoom = 1.0 + 0.15 * max(0, 1 - t / 0.35) ** 2 if i == 0 else 1.0 + 0.05 * j / n
                hook_frame(photo, bg, zoom, top, brand).save(f"{tmp}/{k:05d}.jpg", quality=90)
                k += 1
        bg = tuple(scenes[0].get("bg") or brand.get("bg") or BGS[0])
        for j in range(int(HOOK_END_S * FPS)):
            hook_frame(photos[0], bg, 1.0 + 0.04 * j / (HOOK_END_S * FPS),
                       [reel.get("hook_end", end.get("title", "Order yours today"))], brand, order
                       ).save(f"{tmp}/{k:05d}.jpg", quality=90)
            k += 1
        beat_wav(f"{tmp}/beat.wav", k / FPS)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", f"{tmp}/%05d.jpg", "-i", f"{tmp}/beat.wav",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-crf", "20", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        str(out)], check=True)
    print(f"{out.relative_to(ROOT)}: {k / FPS:.1f}s")


def build(reel):
    if reel.get("hook"):
        return build_hook(reel)
    frames = []
    brand = reel.get("brand", {})
    for i, s in enumerate(reel["scenes"]):
        photo = load(s["image"], s.get("crop")) if s.get("image") else None
        bg = tuple(s.get("bg") or brand.get("bg") or BGS[i % len(BGS)])
        n = int(SCENE_S * FPS)
        frames.append([scene_frame(photo, s.get("headline", ""), s.get("subline", ""), bg, 1 + 0.06 * k / n,
                                   brand, s.get("overlay"), s.get("big"))
                       for k in range(n)])
    end = reel.get("end", {})
    frames.append([end_frame(end.get("title", "Order yours today"),
                             end.get("lines", ["WhatsApp 95793 06816", "flinoshprints.com"]),
                             end.get("foot", "Designed in Goa · delivered across India"), brand)]
                  * int(END_S * FPS))
    fade = int(FADE_S * FPS)
    out = OUT / f"{reel['name']}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        for s, scene in enumerate(frames):
            for i, fr in enumerate(scene):
                if s + 1 < len(frames) and i >= len(scene) - fade:
                    fr = Image.blend(fr, frames[s + 1][0], (i - (len(scene) - fade) + 1) / fade)
                fr.save(f"{tmp}/{k:05d}.jpg", quality=92)
                k += 1
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", f"{tmp}/%05d.jpg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-crf", "18", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart",
                        str(out)], check=True)
    print(f"{out.relative_to(ROOT)}: {k / FPS:.1f}s")


def main():
    reels = json.loads(REELS.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:]
    if names == ["--all"]:
        names = [r["name"] for r in reels]
    for reel in reels:
        if names and reel["name"] not in names:
            continue
        if not names and (OUT / f"{reel['name']}.mp4").exists():
            continue
        build(reel)


if __name__ == "__main__":
    main()
