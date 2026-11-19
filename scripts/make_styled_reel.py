"""Styled flat-lay Reels (1080x1920) on a marble table, built from Flinosh product photos.

Animated composite, not filmed footage: a stack of cards on marble, a vellum sheet
and satin ribbon wrapping one card, the card lifted beside its envelope, extras
fanned out, then the order card. Watermark on every product image, logo footer on
every frame.

    python3 scripts/make_styled_reel.py SPEC.json OUT.mp4
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_reel import ROOT, W, H, FPS, INK, PINK, GOLD, SERIF, SANS, font, fit, centred, footer, end_frame  # noqa
from make_post_cards import watermark  # noqa


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def cutout(path, box=None, thresh=26):
    """Load an image and make the white studio background transparent (flood from the edges)."""
    im = Image.open(ROOT / path).convert("RGB")
    if box:
        im = im.crop(box)
    w, h = im.size
    pad = Image.new("RGB", (w + 2, h + 2), (255, 255, 255))
    pad.paste(im, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), (255, 0, 255), thresh=thresh)
    px = pad.crop((1, 1, w + 1, h + 1))
    alpha = Image.eval(px.convert("RGB").split()[1], lambda v: 255)
    mk = Image.new("L", (w, h), 255)
    a, src = mk.load(), px.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] == (255, 0, 255):
                a[x, y] = 0
    mk = mk.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    out = im.convert("RGBA")
    out.putalpha(mk)
    bb = mk.getbbox()
    return out.crop(bb) if bb else out


def white_envelope(w=805, h=583):
    """A plain white 5x7 (A7) envelope seen from the back: flap and side seams."""
    env = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(env)
    d.rectangle((0, 0, w - 1, h - 1), fill=(252, 252, 250, 255), outline=(222, 222, 218, 255), width=2)
    d.line((0, h - 1, w * 0.5, h * 0.52, w - 1, h - 1), fill=(228, 228, 224, 255), width=3)  # bottom seams
    d.polygon([(0, 0), (w - 1, 0), (w * 0.5, h * 0.58)], fill=(247, 247, 244, 255), outline=(220, 220, 215, 255))
    shade = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(v * 0.06))
    env.alpha_composite(Image.merge("RGBA", (Image.new("L", (w, h), 120),) * 3 + (shade,)))
    a = Image.new("L", (w, h), 255)
    env.putalpha(a)
    return env


def marked(img):
    img = img.copy()
    wm = watermark(img.size)
    a = img.split()[3]
    img.alpha_composite(wm)
    img.putalpha(a)
    return img


def table():
    m = Image.open(ROOT / "assets/marble-light.webp").convert("RGB")
    s = max(W / m.width, H / m.height) * 1.15
    m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
    return m


def bg_frame(marble, zoom=1.0, dx=0):
    z = marble.resize((int(marble.width * zoom), int(marble.height * zoom)), Image.LANCZOS) if zoom != 1 else marble
    x = (z.width - W) // 2 + int(dx)
    y = (z.height - H) // 2
    im = z.crop((x, y, x + W, y + H))
    # soft window light from the top left
    grad = Image.linear_gradient("L").rotate(-35, expand=True).resize((W, H))
    light = Image.new("RGB", (W, H), (255, 250, 240))
    return Image.composite(im, light, grad.point(lambda v: 150 + v // 3))


def place(im, piece, cx, cy, scale=1.0, angle=0.0, lift=0.0):
    p = piece.resize((max(1, int(piece.width * scale)), max(1, int(piece.height * scale))), Image.LANCZOS)
    if angle:
        p = p.rotate(angle, expand=True, resample=Image.BICUBIC)
    off = int(8 + 40 * lift)
    blur = int(10 + 30 * lift)
    sh = Image.new("RGBA", (p.width + 4 * blur, p.height + 4 * blur), (0, 0, 0, 0))
    sh.paste((40, 30, 20, int(110 - 40 * lift)), (2 * blur, 2 * blur), p.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(sh, (int(cx - p.width / 2 - 2 * blur + off), int(cy - p.height / 2 - 2 * blur + off)), sh)
    im.paste(p, (int(cx - p.width / 2), int(cy - p.height / 2)), p)


def stack(card, n=14):
    """A stack of cards: the card on top, paper edges below."""
    w, h = card.size
    dep = n * 4
    st = Image.new("RGBA", (w + dep, h + dep), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    for i in range(n, 0, -1):
        o = i * 4
        shade = 236 - (i % 3) * 8
        d.rectangle((o, o, o + w - 1, o + h - 1), fill=(shade, shade, shade - 4, 255), outline=(205, 200, 192, 255))
    st.paste(card, (0, 0), card)
    return st


def caption(im, text, sub=None, y=1440):
    d = ImageDraw.Draw(im, "RGBA")
    f = fit(d, text, SERIF, 70, 900)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle(((W - tw) / 2 - 50, y - 30, (W + tw) / 2 + 50, y + (190 if sub else 110)), 36,
                        fill=(255, 252, 246, 225))
    centred(d, y, text, f, INK)
    if sub:
        centred(d, y + 100, sub, fit(d, sub, SANS, 42, 860), GOLD)


def build(spec, out):
    marble = table()
    card = marked(cutout(spec["card"], spec.get("card_box"), spec.get("thresh", 26)))
    cs = min(560 / card.width, 780 / card.height)
    card = card.resize((int(card.width * cs), int(card.height * cs)), Image.LANCZOS)
    env = None
    if spec.get("envelope") == "white-5x7":
        env = white_envelope(int(card.width * 7.25 / 5), int(card.height * 5.25 / 7))
    elif spec.get("envelope"):
        env = marked(cutout(spec["envelope"]))
    extra = marked(cutout(spec["extra"], spec.get("extra_box"))) if spec.get("extra") else None
    ribbon = tuple(spec.get("ribbon", [178, 24, 40]))
    st = stack(card)

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)

    def emit(im):
        footer(im, ImageDraw.Draw(im), {})
        proc.stdin.write(im.convert("RGB").tobytes())

    S = lambda s: int(s * FPS)  # noqa

    # 1. the stack on the table, slow push-in
    n = S(3.4)
    for i in range(n):
        t = i / n
        im = bg_frame(marble, 1 + 0.06 * t)
        place(im, st, W / 2 + 10, 800, 1.0 + 0.08 * t, -6 + 2 * t)
        if i > S(0.3):
            caption(im, spec["hook"], spec.get("hook_sub"))
        emit(im)

    # 2. vellum sheet slides over the top card, ribbon wraps, bow
    n = S(4.6)
    cx, cy = W / 2, 800
    for i in range(n):
        t = i / n
        im = bg_frame(marble, 1.06)
        place(im, card, cx, cy, 1.05, 0)
        cw, ch = int(card.width * 1.05), int(card.height * 1.05)
        x0, y0 = cx - cw / 2, cy - ch / 2
        vp = ease(t / 0.35)
        if vp > 0:  # frosted vellum
            vx = lerp(W + 40, x0 - 14, vp)
            reg = im.crop((int(vx), int(y0 - 14), int(vx + cw + 28), int(y0 + ch + 14)))
            fro = reg.filter(ImageFilter.GaussianBlur(5))
            fro = Image.blend(fro, Image.new("RGB", fro.size, (250, 250, 252)), 0.42)
            im.paste(fro, (int(vx), int(y0 - 14)))
            ImageDraw.Draw(im).rectangle((vx, y0 - 14, vx + cw + 27, y0 + ch + 13), outline=(225, 225, 230), width=2)
        rp = ease((t - 0.4) / 0.3)
        d = ImageDraw.Draw(im, "RGBA")
        if rp > 0:  # satin ribbon drawn down the card
            rw = 54
            d.rectangle((cx - rw / 2, y0 - 30, cx + rw / 2, lerp(y0 - 30, y0 + ch + 30, rp)), fill=ribbon + (255,))
            d.rectangle((cx - rw / 2 + 8, y0 - 30, cx - rw / 2 + 16, lerp(y0 - 30, y0 + ch + 30, rp)),
                        fill=(255, 255, 255, 60))
        bp = ease((t - 0.72) / 0.14)
        if bp > 0:  # bow
            by = cy + ch * 0.12
            r = 70 * bp
            dark = tuple(max(0, c - 40) for c in ribbon) + (255,)
            d.polygon([(cx, by), (cx - 2.2 * r, by - 1.1 * r), (cx - 2.0 * r, by + 1.0 * r)], fill=ribbon + (255,))
            d.polygon([(cx, by), (cx + 2.2 * r, by - 1.1 * r), (cx + 2.0 * r, by + 1.0 * r)], fill=ribbon + (255,))
            d.polygon([(cx - 10, by), (cx - 1.1 * r, by + 2.6 * r), (cx - 0.5 * r, by + 2.4 * r)], fill=dark)
            d.polygon([(cx + 10, by), (cx + 1.1 * r, by + 2.6 * r), (cx + 0.5 * r, by + 2.4 * r)], fill=dark)
            d.ellipse((cx - 0.45 * r, by - 0.45 * r, cx + 0.45 * r, by + 0.45 * r), fill=dark)
        caption(im, spec["wrap"], spec.get("wrap_sub"))
        emit(im)

    # 3. a card lifted beside its envelope
    n = S(3.6)
    for i in range(n):
        t = ease(i / (n * 0.7))
        im = bg_frame(marble, 1.06, dx=-20 * t)
        if env is not None:
            es = 1.0 if spec.get("envelope") == "white-5x7" else 640 / env.width
            place(im, env, 330, 1060, es, 12)
            place(im, env, 820, 470, es * 0.9, -18)
        place(im, card, lerp(W / 2, W / 2 + 40, t), lerp(820, 760, t), lerp(1.0, 1.12, t), lerp(0, -7, t), lift=t)
        caption(im, spec["lift"], spec.get("lift_sub"))
        emit(im)

    # 4. extras fanned out
    if extra is not None:
        n = S(3.4)
        es = min(860 / extra.width, 900 / extra.height)
        for i in range(n):
            t = ease(i / (n * 0.6))
            im = bg_frame(marble, 1.04 + 0.03 * i / n)
            place(im, extra, W / 2, lerp(900, 820, t), es * lerp(0.85, 1.0, t), lerp(8, 0, t), lift=0.3 * (1 - t))
            caption(im, spec["extra_text"], spec.get("extra_sub"))
            emit(im)

    end = end_frame(spec["end_title"], ["WhatsApp 95793 06816", "Search Flinosh Prints on Amazon"],
                    spec.get("end_foot", "Designed & printed in Goa"))
    for _ in range(S(3.6)):
        proc.stdin.write(end.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    build(json.load(open(sys.argv[1])), sys.argv[2])
