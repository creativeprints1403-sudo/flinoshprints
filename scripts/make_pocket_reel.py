"""Pocket-fold invite Reel (1080x1920): wood-slat wall, wooden table, a pocket folder
with twine, wax seal and baby's breath opens to reveal the Flinosh invite.

Animated composite from Flinosh product photos (not filmed). Watermark on the card,
logo footer on every frame.

    python3 scripts/make_pocket_reel.py SPEC.json OUT.mp4
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_reel import W, H, FPS, footer, end_frame  # noqa
from make_styled_reel import cutout, marked, white_envelope, caption, place, ease, lerp  # noqa


def backdrop():
    im = Image.new("RGB", (W, H), (190, 140, 92))
    d = ImageDraw.Draw(im)
    wall_h = 1180
    for x in range(-10, W, 46):  # slats
        d.rectangle((x, 0, x + 30, wall_h), fill=(205, 156, 104))
        d.rectangle((x + 30, 0, x + 46, wall_h), fill=(150, 102, 62))
        d.line((x + 3, 0, x + 3, wall_h), fill=(222, 178, 128), width=4)
    rnd = random.Random(3)
    d.rectangle((0, wall_h, W, H), fill=(196, 146, 94))  # table
    for k in range(60):
        y = wall_h + rnd.randint(0, H - wall_h)
        d.line((0, y, W, y + rnd.randint(-20, 20)), fill=(180, 128, 80), width=rnd.randint(1, 4))
    d.line((0, wall_h, W, wall_h), fill=(120, 80, 48), width=6)
    # vase with flowers on the left, out of focus
    d.polygon([(40, 1180), (210, 1180), (240, 900), (190, 820), (60, 820), (10, 900)], fill=(240, 238, 232))
    d.polygon([(125, 820), (190, 820), (240, 900), (210, 1180), (125, 1180)], fill=(222, 220, 214))
    for k in range(9):
        x = 60 + rnd.randint(0, 160)
        d.line((125, 830, x, 380 + rnd.randint(0, 250)), fill=(96, 120, 80), width=6)
    for k in range(14):
        x, y = 30 + rnd.randint(0, 230), 300 + rnd.randint(0, 330)
        r = rnd.randint(40, 80)
        col = rnd.choice([(244, 238, 240), (236, 226, 196), (226, 214, 228)])
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    left = im.crop((0, 0, 330, H)).filter(ImageFilter.GaussianBlur(9))
    im = im.filter(ImageFilter.GaussianBlur(3))
    im.paste(left, (0, 0))
    # warm window light
    grad = Image.linear_gradient("L").rotate(-60, expand=True).resize((W, H))
    return Image.composite(im, Image.new("RGB", (W, H), (255, 236, 205)), grad.point(lambda v: 175 + v // 4))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def pocket_layer(card, colour, flap_t, card_dy, seal_col, show_card=True):
    """Return an RGBA layer of the pocket folder with the card inside. flap_t 0 closed .. 1 open."""
    cw, ch = card.size
    pw, ph = cw + 40, ch + 30
    pad = 400
    L = Image.new("RGBA", (pw + 2 * pad, ph + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    ox, oy = pad, pad
    d.rectangle((ox, oy, ox + pw, oy + ph), fill=shade(colour, 0.82) + (255,))  # back panel
    if show_card:
        L.alpha_composite(card, (ox + 20, int(oy + 15 - card_dy)))
    # bottom pocket strip holds the card
    d.rectangle((ox, oy + ph - 120, ox + pw, oy + ph), fill=shade(colour, 0.92) + (255,))
    fw = int(pw * 0.62 * (1 - flap_t))
    if fw > 2:  # front flap folding open to the left
        k = 1 - 0.35 * flap_t
        d.rectangle((ox, oy, ox + fw, oy + ph), fill=shade(colour, k) + (255,))
        d.line((ox + fw, oy, ox + fw, oy + ph), fill=shade(colour, 0.7) + (255,), width=3)
    if flap_t < 0.05:  # twine and seal (closed)
        ty = oy + ph * 0.48
        d.line((ox - 6, ty - 14, ox + pw + 6, ty + 10), fill=(150, 120, 60, 255), width=4)
        d.line((ox - 6, ty + 10, ox + pw + 6, ty - 14), fill=(150, 120, 60, 255), width=4)
        sx, sy, r = ox + pw * 0.3, ty, 66
        d.ellipse((sx - r - 6, sy - r + 4, sx + r + 2, sy + r + 8), fill=shade(seal_col, 0.7) + (255,))
        d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=seal_col + (255,))
        d.ellipse((sx - r * 0.7, sy - r * 0.7, sx + r * 0.7, sy + r * 0.7), outline=shade(seal_col, 0.75) + (255,), width=5)
        d.ellipse((sx - r * 0.5, sy - r * 0.62, sx - r * 0.1, sy - r * 0.3), fill=shade(seal_col, 1.25) + (200,))
        rnd = random.Random(5)
        for k in range(26):  # baby's breath
            bx, by = sx - 50 + rnd.randint(0, 100), sy - r - 20 - rnd.randint(0, 70)
            d.line((sx, sy - r + 6, bx, by), fill=(150, 160, 110, 255), width=2)
            rr = rnd.randint(6, 10)
            d.ellipse((bx - rr, by - rr, bx + rr, by + rr), fill=(246, 238, 214, 255))
    return L, (ox, oy, pw, ph)


def build(spec, out):
    bg = backdrop()
    card = marked(cutout(spec["card"], spec.get("card_box"), spec.get("thresh", 6)))
    k = min(600 / card.width, 860 / card.height)
    card = card.resize((int(card.width * k), int(card.height * k)), Image.LANCZOS)
    colour = tuple(spec.get("pocket", [150, 168, 110]))
    seal = tuple(spec.get("seal", [214, 158, 60]))
    env = white_envelope(int(card.width * 7.25 / 5), int(card.height * 5.25 / 7))

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)

    def emit(im):
        footer(im, ImageDraw.Draw(im), {"ink": (255, 255, 255)})
        proc.stdin.write(im.convert("RGB").tobytes())

    S = lambda s: int(s * FPS)  # noqa

    def frame(flap, dy, ang, sc, lift, text, sub, sway=0.0):
        im = bg.copy()
        L, _ = pocket_layer(card, colour, flap, dy, seal)
        place(im, L, W / 2 + 60 + sway, 900, sc, ang, lift)
        caption(im, text, sub)
        return im

    n = S(3.2)  # closed, held up, gentle sway
    for i in range(n):
        t = i / n
        emit(frame(0, 0, -5 + 2 * math.sin(t * 3), 0.92 + 0.05 * t, 0.5, spec["hook"], spec.get("hook_sub"),
                   sway=10 * math.sin(t * 4)))
    n = S(2.6)  # flap opens
    for i in range(n):
        t = ease(i / (n * 0.8))
        emit(frame(t, 0, -3, 0.97, 0.5, spec["open"], spec.get("open_sub")))
    n = S(3.2)  # card rises out of the pocket
    for i in range(n):
        t = ease(i / (n * 0.75))
        emit(frame(1, t * card.height * 0.55, -3 + 2 * t, 0.97, 0.5, spec["reveal"], spec.get("reveal_sub")))
    n = S(3.0)  # card on the table beside its envelope
    for i in range(n):
        t = ease(i / (n * 0.6))
        im = bg.copy()
        place(im, env, 380, 1500, 0.9, 8, 0)
        place(im, card, lerp(W / 2, 640, t), lerp(820, 1250, t), lerp(1.0, 0.8, t), lerp(-2, -6, t), lift=0.6 * (1 - t))
        caption(im, spec["table"], spec.get("table_sub"), y=330)
        emit(im)
    end = end_frame(spec["end_title"], ["WhatsApp 95793 06816", "Search Flinosh Prints on Amazon"],
                    spec.get("end_foot", "Designed & printed in Goa"))
    for _ in range(S(3.6)):
        proc.stdin.write(end.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    build(json.load(open(sys.argv[1])), sys.argv[2])
