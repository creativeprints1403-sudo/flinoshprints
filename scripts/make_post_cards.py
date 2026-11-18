"""Make premium, watermarked 4:5 Instagram post images (1080x1350 JPG).

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
W, H = 1080, 1350
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


def load(src):
    if src.startswith(SITE):
        im = Image.open(ROOT / src[len(SITE):])
    else:
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            im = Image.open(io.BytesIO(r.read()))
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
    """A tiled, diagonal 'FLINOSH PRINTS' layer to lay over the photo."""
    side = int((size[0] ** 2 + size[1] ** 2) ** 0.5) + 200
    layer = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(BOLD, 38)
    text = "© FLINOSH PRINTS"
    step_x, step_y = int(d.textlength(text, font=f)) + 120, 150
    for row, y in enumerate(range(0, side, step_y)):
        for x in range(-step_x + (row % 2) * step_x // 2, side, step_x):
            d.text((x + 2, y + 2), text, font=f, fill=(0, 0, 0, 34))
            d.text((x, y), text, font=f, fill=(255, 255, 255, 70))
    layer = layer.rotate(30, resample=Image.BICUBIC)
    left, top = (side - size[0]) // 2, (side - size[1]) // 2
    return layer.crop((left, top, left + size[0], top + size[1]))


def card(p, photo):
    im = Image.new("RGB", (W, H), CREAM)
    grad = Image.linear_gradient("L").resize((W, H))
    im = Image.composite(Image.new("RGB", (W, H), CREAM2), im, grad)
    d = ImageDraw.Draw(im)

    # PREMIUM QUALITY label and product name
    label, lf = "PREMIUM QUALITY", font(BOLD, 26)
    lw = d.textlength(label, font=lf) + 8 * len(label)
    d.rounded_rectangle(((W - lw) / 2 - 28, 46, (W + lw) / 2 + 28, 96), 25, outline=GOLD, width=3)
    x = (W - lw) / 2
    for ch in label:
        d.text((x, 57), ch, font=lf, fill=GOLD)
        x += d.textlength(ch, font=lf) + 8
    tf = fit(d, p["title"], SERIF, 70, 960, 44)
    d.text(((W - d.textlength(p["title"], font=tf)) / 2, 118), p["title"], font=tf, fill=INK)

    # photo on a white panel with a soft shadow and the watermark on top
    box = (70, 228, W - 70, 1000)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + 14, box[2], box[3] + 14), 36, fill=(80, 50, 20, 60))
    im.paste(shadow.filter(ImageFilter.GaussianBlur(18)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, 36, fill="white")
    pw, ph = box[2] - box[0] - 60, box[3] - box[1] - 60
    scale = min(pw / photo.width, ph / photo.height)
    ph_im = photo.resize((int(photo.width * scale), int(photo.height * scale)), Image.LANCZOS)
    px = box[0] + (box[2] - box[0] - ph_im.width) // 2
    py = box[1] + (box[3] - box[1] - ph_im.height) // 2
    im.paste(ph_im, (px, py))
    wm = watermark(ph_im.size)
    im.paste(wm, (px, py), wm)
    logo = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    logo.thumbnail((110, 110))
    logo.putalpha(logo.getchannel("A").point(lambda a: a * 0.8))
    im.paste(logo, (box[2] - logo.width - 24, box[3] - logo.height - 24), logo)
    d = ImageDraw.Draw(im)

    # three feature points
    ff = font(SANS, 28)
    cw, gap, top = 300, 20, 1030
    for i, feat in enumerate(p["features"][:3]):
        x0 = (W - 3 * cw - 2 * gap) // 2 + i * (cw + gap)
        d.rounded_rectangle((x0, top, x0 + cw, top + 108), 22, fill="white", outline=(230, 214, 186), width=2)
        cx, cy = x0 + 36, top + 54
        d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=GOLD)
        d.line([(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 7)], fill="white", width=4)
        lines = wrap(d, feat, ff, cw - 86)[:2]
        ty = cy - 18 * len(lines)
        for line in lines:
            d.text((x0 + 66, ty), line, font=ff, fill=INK)
            ty += 36

    # usage line
    if p.get("use"):
        use = "Perfect for: " + p["use"]
        uf = fit(d, use, SANS, 32, 960)
        d.text(((W - d.textlength(use, font=uf)) / 2, 1162), use, font=uf, fill=GOLD)

    # shop strip
    d.rectangle((0, H - 120, W, H), fill=INK)
    mark = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    mark.thumbnail((76, 76))
    im.paste(mark, (48, H - 98), mark)
    d.text((140, H - 82), "Flinosh Prints", font=font(SERIF, 42), fill="white")
    shop = "Shop on Amazon · WhatsApp 95793 06816"
    sf = fit(d, shop, BOLD, 30, 480)
    d.text((W - 48 - d.textlength(shop, font=sf), H - 76), shop, font=sf, fill=(255, 214, 120))
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
                card(p, load(p["image"])).save(ROOT / name, quality=90, optimize=True)
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
