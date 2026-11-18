"""Make premium, watermarked 4:5 Instagram post images (1440x1800 JPG).

Each product in social/instagram-products.json that has a "title" gets an
Amazon-style card: a PREMIUM QUALITY label, the product name, the photo on a
white panel under a tiled Flinosh Prints watermark, three feature points, a
"Perfect for" line and a shop strip. Cards go to assets/ig/<photo-name>.jpg
and the product's "card" field points there; the poster uses the card once
it exists. Needs Pillow.

    python3 scripts/make_post_cards.py           # build cards not built yet
    python3 scripts/make_post_cards.py --all     # rebuild every card
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "social" / "instagram-products.json"
OUT = ROOT / "assets" / "ig"
SITE = "https://flinoshprints.com/"
# Instagram takes photos up to 1440 px wide, so cards are drawn at that size.
W, H = 1440, 1800
K = W / 1080
INK, GOLD, CREAM, CREAM2 = (52, 36, 24), (176, 132, 52), (251, 246, 237), (243, 233, 216)


def first(*paths):
    return next((p for p in paths if Path(p).exists()), paths[-1])


SERIF = first("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
SANS = first("/usr/share/fonts/opentype/inter/Inter-Medium.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD = first("/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def slug(p):
    return Path(p["image"].split("?")[0]).name.split(".")[0].replace("+", "-")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def load(src):
    """The sharpest copy of a photo: the site's full-size original if it is
    bigger than the Pinterest JPG, or Amazon's 2000 px version."""
    if src.startswith(SITE):
        path = ROOT / src[len(SITE):]
        im = Image.open(path)
        big = ROOT / "assets" / (path.stem + ".webp")
        if big.exists() and Image.open(big).width > im.width:
            im = Image.open(big)
    else:
        try:
            im = fetch(src.replace("._SL1080_.", "._SL2000_."))
        except Exception:
            im = fetch(src)
    return im.convert("RGB")


def fit(d, text, path, size, width, low=26):
    while d.textlength(text, font=font(path, size)) > width and size > low:
        size -= 2
    return font(path, size)


def wrap(d, text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if line and d.textlength(trial, font=f) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def watermark(size):
    """One faint, gently angled 'FLINOSH PRINTS' mark across the middle of the photo."""
    w, h = size
    text = "© FLINOSH PRINTS"
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f = fit(probe, text, BOLD, max(28, int(w * 0.11)), int(w * 0.8), 20)
    tw, th = int(probe.textlength(text, font=f)), f.size
    layer = Image.new("RGBA", (tw + 20, th + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((12, 8), text, font=f, fill=(60, 40, 20, 40))
    d.text((10, 6), text, font=f, fill=(255, 255, 255, 110))
    layer = layer.rotate(18, expand=True, resample=Image.BICUBIC)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(layer, ((w - layer.width) // 2, (h - layer.height) // 2), layer)
    return out


def card(p, photo):
    def s(v):  # layout is designed at 1080 wide and drawn at W
        return round(v * K)

    im = Image.new("RGB", (W, H), CREAM)
    grad = Image.linear_gradient("L").resize((W, H))
    im = Image.composite(Image.new("RGB", (W, H), CREAM2), im, grad)
    d = ImageDraw.Draw(im)

    # PREMIUM QUALITY label and product name
    label, lf = "PREMIUM QUALITY", font(BOLD, s(26))
    lw = d.textlength(label, font=lf) + s(8) * len(label)
    d.rounded_rectangle(((W - lw) / 2 - s(28), s(46), (W + lw) / 2 + s(28), s(96)), s(25), outline=GOLD, width=s(3))
    x = (W - lw) / 2
    for ch in label:
        d.text((x, s(57)), ch, font=lf, fill=GOLD)
        x += d.textlength(ch, font=lf) + s(8)
    tf = fit(d, p["title"], SERIF, s(70), s(960), s(44))
    d.text(((W - d.textlength(p["title"], font=tf)) / 2, s(118)), p["title"], font=tf, fill=INK)

    # photo on a white panel with a soft shadow and the watermark on top
    box = (s(70), s(228), W - s(70), s(1000))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + s(14), box[2], box[3] + s(14)), s(36),
                                             fill=(80, 50, 20, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(18)))
    im.paste(shadow, (0, 0), shadow)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, s(36), fill="white")
    pw, ph = box[2] - box[0] - s(60), box[3] - box[1] - s(60)
    scale = min(pw / photo.width, ph / photo.height)
    ph_im = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    if scale < 1:  # a light sharpen keeps fine print crisp after shrinking
        ph_im = ph_im.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    px = box[0] + (box[2] - box[0] - ph_im.width) // 2
    py = box[1] + (box[3] - box[1] - ph_im.height) // 2
    im.paste(ph_im, (px, py))
    wm = watermark(ph_im.size)
    im.paste(wm, (px, py), wm)
    logo = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    logo.thumbnail((s(110), s(110)))
    logo.putalpha(logo.getchannel("A").point(lambda a: a * 0.8))
    im.paste(logo, (box[2] - logo.width - s(24), box[3] - logo.height - s(24)), logo)
    d = ImageDraw.Draw(im)

    # three feature points
    ff = font(SANS, s(28))
    cw, gap, top = s(300), s(20), s(1030)
    for i, feat in enumerate(p["features"][:3]):
        x0 = (W - 3 * cw - 2 * gap) // 2 + i * (cw + gap)
        d.rounded_rectangle((x0, top, x0 + cw, top + s(108)), s(22), fill="white", outline=(230, 214, 186), width=s(2))
        cx, cy = x0 + s(36), top + s(54)
        d.ellipse((cx - s(18), cy - s(18), cx + s(18), cy + s(18)), fill=GOLD)
        d.line([(cx - s(8), cy), (cx - s(2), cy + s(7)), (cx + s(9), cy - s(7))], fill="white", width=s(4))
        lines = wrap(d, feat, ff, cw - s(86))[:2]
        ty = cy - s(18) * len(lines)
        for line in lines:
            d.text((x0 + s(66), ty), line, font=ff, fill=INK)
            ty += s(36)

    # usage line
    if p.get("use"):
        use = "Perfect for: " + p["use"]
        uf = fit(d, use, SANS, s(32), s(960))
        d.text(((W - d.textlength(use, font=uf)) / 2, s(1162)), use, font=uf, fill=GOLD)

    # shop strip
    d.rectangle((0, H - s(120), W, H), fill=INK)
    mark = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    mark.thumbnail((s(76), s(76)))
    im.paste(mark, (s(48), H - s(98)), mark)
    d.text((s(140), H - s(82)), "Flinosh Prints", font=font(SERIF, s(42)), fill="white")
    shop = "Shop on Amazon · WhatsApp 95793 06816"
    sf = fit(d, shop, BOLD, s(30), s(480))
    d.text((W - s(48) - d.textlength(shop, font=sf), H - s(76)), shop, font=sf, fill=(255, 214, 120))
    return im


def main():
    products = json.loads(PRODUCTS.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    rebuild = "--all" in sys.argv
    changed = False
    for p in products:
        if not p.get("title"):
            continue
        name = f"assets/ig/{slug(p)}.jpg"
        if rebuild or not (ROOT / name).exists():
            try:
                card(p, load(p["image"])).save(ROOT / name, quality=95, subsampling=0, optimize=True)
                print("built", name)
            except Exception as e:  # keep going; the poster falls back to the photo
                print("skipped", p["image"], e)
                continue
        if p.get("card") != name:
            p["card"] = name
            changed = True
    if changed:
        PRODUCTS.write_text(json.dumps(products, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
