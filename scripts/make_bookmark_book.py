"""Bookmarks shown in open books: 4:5 post images and a 9:16 Reel.

Composite from Flinosh bookmark photos (not filmed): an open book on a table,
the bookmark lying in it with its tassel out over the top. Watermark on the
bookmark, logo on every image/frame.

    python3 scripts/make_bookmark_book.py OUT_DIR bookmark1.png [bookmark2.png ...]
"""
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_reel import ROOT, footer, end_frame, font, fit, centred, SERIF, SANS, INK, GOLD  # noqa
from make_post_cards import watermark  # noqa

PAPER = (249, 244, 232)


def page(w, h, side, seed):
    rnd = random.Random(seed)
    pg = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(pg)
    m = 70
    y = 110
    while y < h - 90:  # lines of "text"
        x = m + (24 if rnd.random() < 0.12 else 0)
        end = w - m - (rnd.randint(40, 200) if rnd.random() < 0.1 else 0)
        while x < end:
            ww = rnd.randint(18, 70)
            d.rectangle((x, y, min(x + ww, end), y + 7), fill=(150, 142, 130))
            x += ww + 11
        y += 25 if rnd.random() > 0.08 else 50
    d.text((w // 2 - 10, h - 60), str(rnd.randint(40, 300)), fill=(150, 142, 130), font=font(SANS, 22))
    pg = pg.filter(ImageFilter.GaussianBlur(0.6))
    # gutter shadow and page curve
    g = Image.linear_gradient("L").rotate(90 if side == "L" else -90, expand=True).resize((w, h))
    g = g.point(lambda v: int(max(0, v - 150) * 1.4))
    shade = Image.new("RGB", (w, h), (120, 105, 85))
    return Image.composite(shade, pg, g)


def book(w=1000, h=720, cover=(92, 40, 36), seed=1):
    L = Image.new("RGBA", (w + 60, h + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((0, 8, w + 60, h + 50), 18, fill=cover + (255,))
    for k in range(6):  # page edges at the outer sides
        d.rectangle((14 - k, 18 + k, w // 2 + 30, h + 32 - k), fill=(232 - 6 * k, 226 - 6 * k, 212 - 6 * k, 255))
        d.rectangle((w // 2 + 30, 18 + k, w + 46 + k, h + 32 - k), fill=(232 - 6 * k, 226 - 6 * k, 212 - 6 * k, 255))
    L.paste(page(w // 2, h, "L", seed), (30, 20))
    L.paste(page(w // 2, h, "R", seed + 1), (30 + w // 2, 20))
    return L


def table(W, H):
    m = Image.open(ROOT / "assets/marble-light.webp").convert("RGB")
    s = max(W / m.width, H / m.height) * 1.1
    m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
    x, y = (m.width - W) // 2, (m.height - H) // 2
    im = m.crop((x, y, x + W, y + H))
    g = Image.linear_gradient("L").rotate(-30, expand=True).resize((W, H))
    return Image.composite(im, Image.new("RGB", (W, H), (255, 246, 232)), g.point(lambda v: 160 + v // 3))


def shadow_paste(im, piece, x, y, blur=16, off=(10, 14), alpha=110):
    a = piece.split()[3]
    sh = Image.new("RGBA", (piece.width + 4 * blur, piece.height + 4 * blur), (0, 0, 0, 0))
    sh.paste((40, 30, 20, alpha), (2 * blur, 2 * blur), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(sh, (int(x - 2 * blur + off[0]), int(y - 2 * blur + off[1])), sh)
    im.paste(piece, (int(x), int(y)), piece)


def scene(W, H, bm, cover, seed, angle=-4, cy=None, zoom=1.0):
    im = table(W, H).convert("RGBA")
    bk = book(cover=cover, seed=seed)
    if zoom != 1:
        bk = bk.resize((int(bk.width * zoom), int(bk.height * zoom)), Image.LANCZOS)
    cy = cy or H * 0.55
    bx, by = (W - bk.width) / 2, cy - bk.height / 2
    # bookmark lies on the right page, tassel over the top edge
    b = bm.copy()
    a = b.split()[3]
    b.alpha_composite(watermark(b.size))
    b.putalpha(a)
    k = (bk.height * 0.95) / b.height
    b = b.resize((int(b.width * k), int(b.height * k)), Image.LANCZOS)
    page_layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow_paste(page_layer, bk, bx, by, blur=22, off=(14, 22), alpha=120)
    shadow_paste(page_layer, b, bx + bk.width * 0.66 - b.width / 2, by - b.height * 0.2, blur=6, off=(5, 7), alpha=90)
    page_layer = page_layer.rotate(angle, center=(W / 2, cy), resample=Image.BICUBIC)
    im.alpha_composite(page_layer)
    return im.convert("RGB")


def caption(im, text, sub, y):
    d = ImageDraw.Draw(im, "RGBA")
    f = fit(d, text, SERIF, 64, 900)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle(((im.width - tw) / 2 - 46, y - 26, (im.width + tw) / 2 + 46, y + (170 if sub else 100)), 34,
                        fill=(255, 252, 246, 225))
    d.text(((im.width - tw) / 2, y), text, font=f, fill=INK)
    if sub:
        sf = fit(d, sub, SANS, 40, 860)
        d.text(((im.width - d.textlength(sub, font=sf)) / 2, y + 92), sub, font=sf, fill=GOLD)


def logo_corner(im):
    lg = Image.open(ROOT / "assets/logo-mark.webp").convert("RGBA")
    lg.thumbnail((110, 110))
    im.paste(lg, (im.width - 140, 30), lg)


COVERS = [(92, 40, 36), (34, 66, 58), (40, 52, 92), (120, 84, 40)]
LINES = [("A page you'll never lose", "Christmas bookmarks with tassels"),
         ("Gift it with a good book", "perfect stocking filler"),
         ("Bright on every page", "thick card, rich colour"),
         ("Set of 4 designs", "Santa · snowman · reindeer · tree")]


def main(out_dir, paths):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bms = [Image.open(p).convert("RGBA") for p in paths]
    for i, bm in enumerate(bms):  # 4:5 post images
        im = scene(1080, 1350, bm, COVERS[i % 4], i * 3, angle=[-4, 3, -2, 5][i % 4], cy=640, zoom=0.98)
        caption(im, *LINES[i % 4], y=1140)
        logo_corner(im)
        im.save(out / f"bookmark-in-book-{i + 1}.jpg", quality=93)
    W, H, FPS = 1080, 1920, 30
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-vf",
                             "crop=1080:1920:12*sin(t*1.1)+12:10*sin(t*1.5+1)+10,scale=1080:1920,vignette=PI/6",
                             "-c:v", "libx264", "-b:v", "4M", "-maxrate", "5M", "-bufsize", "8M",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "bookmarks-in-books.mp4")],
                            stdin=subprocess.PIPE)
    for i, bm in enumerate(bms):
        base = scene(W + 120, H + 200, bm, COVERS[i % 4], i * 3, angle=[-4, 3, -2, 5][i % 4], cy=900)
        n = int(2.8 * FPS)
        for f in range(n):
            z = 1 + 0.06 * f / n
            fr = base.resize((int(base.width * z), int(base.height * z)), Image.LANCZOS)
            x, y = (fr.width - W) // 2, (fr.height - H) // 2
            fr = fr.crop((x, y, x + W, y + H))
            caption(fr, *LINES[i % 4], y=1450)
            footer(fr, ImageDraw.Draw(fr), {})
            proc.stdin.write(fr.tobytes())
    end = end_frame("Shop our Christmas bookmarks", ["WhatsApp 95793 06816", "Search Flinosh Prints on Amazon"],
                    "Order by 18 December for Christmas delivery")
    for _ in range(int(3.6 * FPS)):
        proc.stdin.write(end.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
