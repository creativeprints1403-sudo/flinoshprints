"""Generic red football birthday invite (4x6 in, 1200x1800 px). No real player names or likeness."""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FD = "/usr/share/fonts/opentype/inter/"
W, H = 1200, 1800


def f(name, size):
    return ImageFont.truetype(FD + name, size)


def centred(d, x, y, text, font, fill, **kw):
    d.text((x - d.textlength(text, font=font) / 2, y), text, font=font, fill=fill, **kw)


def ball(r):
    im = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=(245, 245, 245, 255), outline=(30, 30, 30, 255), width=4)
    def pent(cx, cy, s, rot=0):
        pts = [(cx + s * math.cos(rot + k * 2 * math.pi / 5 - math.pi / 2),
                cy + s * math.sin(rot + k * 2 * math.pi / 5 - math.pi / 2)) for k in range(5)]
        d.polygon(pts, fill=(25, 25, 25, 255))
        return pts
    c = pent(r, r, r * 0.3)
    for k in range(5):
        a = k * 2 * math.pi / 5 - math.pi / 2
        x, y = r + r * 0.78 * math.cos(a), r + r * 0.78 * math.sin(a)
        pent(x, y, r * 0.24, a + math.pi)
        d.line((r + r * 0.3 * math.cos(a), r + r * 0.3 * math.sin(a), x, y), fill=(60, 60, 60, 255), width=4)
    shade = Image.new("L", im.size, 0)
    ImageDraw.Draw(shade).ellipse((-r * 0.4, -r * 0.4, r * 1.5, r * 1.5), fill=255)
    shade = shade.filter(ImageFilter.GaussianBlur(r * 0.4))
    dark = Image.new("RGBA", im.size, (0, 0, 0, 90))
    dark.putalpha(Image.eval(shade, lambda v: int((255 - v) * 0.35)))
    out = Image.alpha_composite(im, dark)
    out.putalpha(im.split()[3])
    return out


def player(h):
    """Generic footballer silhouette, arms out in celebration, seen from behind."""
    s = h / 1000
    im = Image.new("RGBA", (int(900 * s), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = (12, 4, 6, 255)
    cx = 450 * s
    d.ellipse((cx - 62 * s, 40 * s, cx + 62 * s, 175 * s), fill=k)  # head
    d.rectangle((cx - 30 * s, 160 * s, cx + 30 * s, 210 * s), fill=k)  # neck
    d.polygon([(cx - 150 * s, 220 * s), (cx + 150 * s, 220 * s), (cx + 120 * s, 560 * s), (cx - 120 * s, 560 * s)], fill=k)
    for sgn in (-1, 1):  # arms out and down
        d.line((cx + sgn * 140 * s, 240 * s, cx + sgn * 330 * s, 470 * s), fill=k, width=int(70 * s))
        d.line((cx + sgn * 330 * s, 470 * s, cx + sgn * 410 * s, 600 * s), fill=k, width=int(56 * s))
        d.ellipse((cx + sgn * 410 * s - 34 * s, 590 * s, cx + sgn * 410 * s + 34 * s, 660 * s), fill=k)
        d.polygon([(cx + sgn * 10 * s, 560 * s), (cx + sgn * 130 * s, 560 * s), (cx + sgn * 170 * s, 700 * s),
                   (cx + sgn * 40 * s, 700 * s)], fill=k)  # shorts
        d.line((cx + sgn * 95 * s, 690 * s, cx + sgn * 190 * s, 950 * s), fill=k, width=int(68 * s))  # legs apart
        d.ellipse((cx + sgn * 190 * s - 55 * s, 925 * s, cx + sgn * 190 * s + 55 * s, 990 * s), fill=k)
    rim = im.filter(ImageFilter.GaussianBlur(10 * s))
    glow = Image.new("RGBA", im.size, (255, 90, 70, 0))
    glow.putalpha(rim.split()[3].point(lambda v: int(v * 0.9)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out


def build(out, name="AARAV", age="7TH", date="Saturday, 12 Dec", time="4:00 PM", venue="Your venue, Goa"):
    rnd = random.Random(7)
    im = Image.new("RGB", (W, H), (120, 6, 14))
    g = Image.radial_gradient("L").resize((W * 2, H * 2)).crop((W // 2, 0, W // 2 + W, H))
    im = Image.composite(Image.new("RGB", (W, H), (70, 0, 6)), Image.new("RGB", (W, H), (220, 24, 36)), g)
    d = ImageDraw.Draw(im, "RGBA")
    for k in range(260):  # crowd / stadium speckle
        x, y = rnd.randint(0, W), rnd.randint(380, 1250)
        d.ellipse((x, y, x + 6, y + 6), fill=(255, 120, 120, rnd.randint(20, 70)))
    for row in (40, 90):  # floodlights
        for x in range(40, W, 110):
            d.ellipse((x, row, x + 26, row + 18), fill=(255, 240, 230, 230))
    glow = im.filter(ImageFilter.GaussianBlur(18))
    im = Image.blend(im, glow, 0.45)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 1450, W, H), fill=(60, 4, 8, 160))  # pitch
    d = ImageDraw.Draw(im, "RGBA")
    gx0, gy0 = 760, 560  # goal net on the right
    d.rectangle((gx0, gy0, W + 20, gy0 + 760), outline=(255, 255, 255, 230), width=14)
    for x in range(gx0, W, 44):
        d.line((x, gy0, x + 60, gy0 + 760), fill=(255, 255, 255, 60), width=3)
        d.line((x + 60, gy0, x, gy0 + 760), fill=(255, 255, 255, 60), width=3)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((700, 980, 1180, 1460), fill=(255, 170, 120, 150))
    halo = halo.filter(ImageFilter.GaussianBlur(60))
    im.paste(halo, (0, 0), halo)
    for k in range(5):  # speed streaks
        yy = 1080 + k * 55
        ImageDraw.Draw(im, "RGBA").line((560 + k * 20, yy, 820, yy + 20), fill=(255, 230, 200, 120), width=6)
    b = ball(210)
    b = b.rotate(18, resample=Image.BICUBIC)
    im.paste(b, (740, 1010), b)
    d = ImageDraw.Draw(im, "RGBA")
    white, gold = (255, 255, 255), (246, 196, 72)
    d.polygon([(70, 120), (640, 95), (660, 190), (60, 215)], fill=(200, 10, 24, 255))
    d.text((110, 112), "YOU'RE", font=f("InterDisplay-BlackItalic.otf", 96), fill=white)
    d.text((80, 215), "INVITED!", font=f("InterDisplay-BlackItalic.otf", 168), fill=white,
           stroke_width=3, stroke_fill=(90, 0, 8))
    d.text((90, 410), "TO A GOAL-SCORING CELEBRATION!", font=f("InterDisplay-BoldItalic.otf", 40), fill=white)
    d.text((110, 500), "Join us as we celebrate", font=f("Inter-SemiBold.otf", 44), fill=white)
    nf = f("InterDisplay-Black.otf", 150)
    while d.textlength(name + "'S", font=nf) > 700:
        nf = f("InterDisplay-Black.otf", nf.size - 6)
    d.text((80, 565), name + "'S", font=nf, fill=gold, stroke_width=3, stroke_fill=(110, 50, 0))
    d.text((90, 745), f"{age}  B I R T H D A Y", font=f("Inter-Bold.otf", 52), fill=white)
    d.polygon([(60, 850), (690, 835), (700, 960), (50, 975)], fill=(20, 0, 2, 200))
    d.text((90, 860), "FOOTBALL PARTY!", font=f("InterDisplay-BlackItalic.otf", 84), fill=gold)
    y = 1030
    for label, val in (("DATE:", date), ("TIME:", time), ("VENUE:", venue)):
        d.polygon([(60, y), (700, y), (720, y + 55), (700, y + 110), (60, y + 110), (80, y + 55)], fill=(110, 0, 10, 230),
                  outline=gold)
        d.ellipse((95, y + 18, 169, y + 92), fill=gold)
        ic = (110, 0, 10)
        if label == "DATE:":
            d.rectangle((114, y + 38, 150, y + 74), outline=ic, width=5); d.line((114, y + 48, 150, y + 48), fill=ic, width=5)
        elif label == "TIME:":
            d.ellipse((112, y + 35, 152, y + 75), outline=ic, width=5); d.line((132, y + 55, 132, y + 42), fill=ic, width=4); d.line((132, y + 55, 143, y + 59), fill=ic, width=4)
        else:
            d.ellipse((118, y + 32, 146, y + 60), outline=ic, width=6); d.polygon([(120, y + 54), (144, y + 54), (132, y + 80)], fill=ic)
        d.text((190, y + 30), label, font=f("Inter-Bold.otf", 40), fill=white)
        d.text((350, y + 28), val, font=f("Inter-Bold.otf", 44), fill=gold)
        y += 135
    centred(d, 460, 1460, "Get ready to dribble, kick and score,", f("Inter-SemiBold.otf", 38), white)
    centred(d, 460, 1510, "just like a champion!", f("Inter-SemiBold.otf", 38), white)
    centred(d, 520, 1610, "“Dream big, play hard, never give up!”", f("Inter-SemiBoldItalic.otf", 40), white)
    im.save(out, quality=95)


if __name__ == "__main__":
    build(sys.argv[1])
