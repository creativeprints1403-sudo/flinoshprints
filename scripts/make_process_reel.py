"""Make animated "from printer to parcel" process Reels (1080x1920 MP4).

An honest motion-graphics illustration (not filmed footage) built from the real
print artwork: the sheet comes out of a drawn printer, cut lines are trimmed,
the pieces are checked and fanned out, then packed into a Flinosh box.
Every frame carries the Flinosh watermark on the artwork and the logo footer.

    python3 scripts/make_process_reel.py OUT.mp4 SHEET_IMAGE BOXES_JSON TITLE PRODUCT
BOXES_JSON is a list of [x0, y0, x1, y1] piece boxes in sheet-image pixels.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_reel import (ROOT, W, H, FPS, INK, PINK, GOLD, SERIF, SANS, SANS_BOLD,  # noqa: E402
                       font, fit, centred, footer, end_frame)
from make_post_cards import watermark  # noqa: E402

CREAM = (252, 247, 240)
MAT = (38, 92, 74)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def caption(d, step, text, sub=None, y=1380):
    if step:
        f = font(SANS_BOLD, 40)
        tw = d.textlength(step, font=f)
        d.rounded_rectangle(((W - tw) / 2 - 30, y - 12, (W + tw) / 2 + 30, y + 58), 34, fill=PINK)
        d.text(((W - tw) / 2, y), step, font=f, fill="white")
    centred(d, y + 95, text, fit(d, text, SERIF, 74), INK)
    if sub:
        centred(d, y + 200, sub, fit(d, sub, SANS, 44), GOLD)


def base(bg=CREAM):
    im = Image.new("RGB", (W, H), bg)
    return im, ImageDraw.Draw(im)


def shadow_paste(im, piece, x, y, blur=14, off=10, alpha=90):
    sh = Image.new("RGBA", (piece.width + 60, piece.height + 60), (0, 0, 0, 0))
    m = piece.split()[3] if piece.mode == "RGBA" else Image.new("L", piece.size, 255)
    sh.paste((0, 0, 0, alpha), (30, 30), m)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(sh, (int(x - 30 + off), int(y - 30 + off)), sh)
    im.paste(piece, (int(x), int(y)), piece if piece.mode == "RGBA" else None)


def draw_printer(d, top, prog, blink):
    x0, x1 = 90, W - 90
    d.rounded_rectangle((x0, top, x1, top + 300), 40, fill=(70, 72, 78))
    d.rounded_rectangle((x0 + 20, top + 20, x1 - 20, top + 130), 26, fill=(92, 95, 102))
    d.rounded_rectangle((x0 + 60, top + 250, x1 - 60, top + 290), 12, fill=(25, 26, 30))  # paper slot
    d.ellipse((x1 - 110, top + 160, x1 - 70, top + 200), fill=(80, 220, 120) if blink else (40, 90, 60))
    d.text((x0 + 60, top + 160), "PRINTING…  %d%%" % int(prog * 100), font=font(SANS_BOLD, 40), fill=(220, 220, 225))


def build(out, sheet_path, boxes, title, product, finale=None, end_foot="Designed & printed in Goa"):
    sheet = Image.open(sheet_path).convert("RGB")
    SW = 1000 if sheet.width > sheet.height else 900
    k = SW / sheet.width
    SH = int(sheet.height * k)
    sheet_s = sheet.resize((SW, SH), Image.LANCZOS)
    wm = watermark(sheet_s.size)
    sheet_wm = sheet_s.convert("RGBA")
    sheet_wm.alpha_composite(wm)
    pieces = []
    for b in boxes:
        bb = [int(v * k) for v in b]
        pc = sheet_s.crop(bb).convert("RGBA")
        pc.alpha_composite(watermark(pc.size))
        pieces.append((bb, pc))
    sx = (W - SW) // 2
    sy_cut = 300 + (1000 - SH) // 2

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                             "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                            stdin=subprocess.PIPE)
    count = [0]

    def emit(im):
        proc.stdin.write(im.tobytes())
        count[0] += 1

    def secs(s):
        return int(s * FPS)

    # 0. hook title
    n = secs(1.8)
    for i in range(n):
        t = ease(i / (n * 0.5))
        im, d = base()
        centred(d, lerp(820, 700, t), "From our printer", font(SERIF, 96), INK)
        centred(d, lerp(940, 820, t), "to your door", font(SERIF, 96), PINK)
        centred(d, 990, product, fit(d, product, SANS, 50), GOLD)
        footer(im, d, {})
        emit(im)

    # 1. printing: the sheet slides out of the slot
    top = 260
    slot = top + 270
    n = secs(3.4)
    for i in range(n):
        p = ease(i / (n - 15))
        im, d = base()
        y = slot - SH + p * (SH + 40)
        vis_top = max(0, int(slot - y))
        if vis_top < SH:
            part = sheet_wm.crop((0, vis_top, SW, SH))
            shadow_paste(im, part, sx, y + vis_top, off=6)
        draw_printer(d, top, p, (i // 8) % 2 == 0)
        caption(d, "STEP 1", "Printed in Goa", "on premium thick card", y=1430)
        footer(im, d, {})
        emit(im)

    # 1b. move to the cutting mat (printer slides up, mat fades in)
    n = secs(1.0)
    y_end = slot + 40
    for i in range(n):
        t = ease(i / (n - 1))
        bg = tuple(int(lerp(c1, c2, t)) for c1, c2 in zip(CREAM, MAT))
        im, d = base(bg)
        shadow_paste(im, sheet_wm, sx, lerp(y_end, sy_cut, t), off=6)
        draw_printer(d, top - 700 * t, 1, True)
        footer(im, d, {"ink": tuple(int(lerp(a, 255, t)) for a in INK)})
        emit(im)

    def mat_bg():
        im, d = base(MAT)
        for gx in range(0, W, 54):
            d.line((gx, 0, gx, H), fill=(52, 110, 90), width=2)
        for gy in range(0, H, 54):
            d.line((0, gy, W, gy), fill=(52, 110, 90), width=2)
        return im, d

    # 2. trimming: guillotine cut lines drawn one after another with a blade
    xs = sorted({bb[0] for bb, _ in pieces} | {bb[2] for bb, _ in pieces})
    ys = sorted({bb[1] for bb, _ in pieces} | {bb[3] for bb, _ in pieces})
    lines = [("v", x) for x in xs] + [("h", y) for y in ys]
    n = secs(4.0)
    per = n / len(lines)
    for i in range(n):
        im, d = mat_bg()
        shadow_paste(im, sheet_wm, sx, sy_cut, off=6)
        for j, (kind, v) in enumerate(lines):
            p = ease((i - j * per) / per)
            if p <= 0:
                continue
            if kind == "v":
                a, b = (sx + v, sy_cut - 30), (sx + v, sy_cut - 30 + p * (SH + 60))
            else:
                a, b = (sx - 30, sy_cut + v), (sx - 30 + p * (SW + 60), sy_cut + v)
            d.line((a, b), fill=(230, 40, 60), width=4)
            if 0 < p < 1:  # the blade
                bx, by = b
                d.polygon([(bx, by), (bx + 26, by - 70), (bx + 46, by - 60)], fill=(205, 210, 218))
                d.rounded_rectangle((bx + 22, by - 190, bx + 56, by - 66), 10, fill=(240, 180, 30))
        d.rounded_rectangle((60, 1380, W - 60, 1700), 40, fill=CREAM)
        caption(d, "STEP 2", "Trimmed by hand", "clean, straight edges", y=1410)
        footer(im, d, {"ink": (255, 255, 255)})
        emit(im)

    # 3. pieces lift off the sheet and fan out for checking
    m = len(pieces)
    fan_w = min(1000 / m, 260)
    scale_f = min(1.35, (fan_w * 0.95) / max(pc.width for _, pc in pieces),
                  700 / max(pc.height for _, pc in pieces))
    n = secs(3.0)
    for i in range(n):
        t = ease(i / (n * 0.7))
        im, d = mat_bg()
        waste = sheet_wm.copy()
        mask = Image.new("L", waste.size, 255)
        md = ImageDraw.Draw(mask)
        for bb, _ in pieces:
            md.rectangle(bb, fill=0)
        a = waste.split()[3].point(lambda v: v)
        waste.putalpha(Image.composite(a.point(lambda v: int(v * (1 - t))), Image.new("L", waste.size, 0), mask))
        im.paste(waste, (sx, sy_cut), waste)
        for j, (bb, pc) in enumerate(pieces):
            s = lerp(1, scale_f, t)
            ang = lerp(0, (j - (m - 1) / 2) * (-4 if m <= 6 else -1.5), t)
            img = pc.resize((max(1, int(pc.width * s)), max(1, int(pc.height * s))), Image.LANCZOS)
            img = img.rotate(ang, expand=True, resample=Image.BICUBIC)
            tx = (W - m * fan_w) / 2 + j * fan_w + fan_w / 2 - img.width / 2 if m <= 6 else None
            if tx is None:  # grids: keep the layout, just spread a little
                cx = sx + (bb[0] + bb[2]) / 2
                cy = sy_cut + (bb[1] + bb[3]) / 2
                tcx = W / 2 + (cx - W / 2) * 1.12
                tcy = sy_cut + SH / 2 + (cy - sy_cut - SH / 2) * 1.12
                x = lerp(cx, tcx, t) - img.width / 2
                y = lerp(cy, tcy, t) - img.height / 2
            else:
                x = lerp(sx + bb[0] + (bb[2] - bb[0]) / 2 - img.width / 2, tx, t)
                y = lerp(sy_cut + bb[1] + (bb[3] - bb[1]) / 2, 330 + 430, t) - img.height / 2
            shadow_paste(im, img, x, y, off=lerp(6, 16, t), alpha=110)
        d.rounded_rectangle((60, 1380, W - 60, 1700), 40, fill=CREAM)
        caption(d, "STEP 3", "Checked one by one", "only perfect pieces go out", y=1410)
        footer(im, d, {"ink": (255, 255, 255)})
        emit(im)
    last_fan = im

    # 4. packing: pieces drop into a kraft box, lid closes, sticker stamps
    box_w, box_h = 760, 420
    bx0, by0 = (W - box_w) // 2, 820
    stack = pieces[0][1]
    st_s = min((box_w - 160) / stack.width, (box_h * 0.95) / stack.height)
    n = secs(3.4)
    logo = Image.open(ROOT / "assets/logo-mark.webp").convert("RGBA")
    logo.thumbnail((150, 150))
    for i in range(n):
        tt = i / n
        im, d = base((245, 238, 228))
        d.rectangle((bx0 - 30, by0 - 40, bx0 + box_w + 30, by0), fill=(150, 108, 66))  # back flap
        # pieces falling in, one after another
        for j, (bb, pc) in enumerate(pieces):
            p = ease((tt - j * 0.35 / m) / 0.3)
            if p <= 0:
                continue
            img = pc.resize((max(1, int(pc.width * st_s)), max(1, int(pc.height * st_s))), Image.LANCZOS)
            x = (W - img.width) / 2 + (j - (m - 1) / 2) * 6
            y = lerp(-img.height - 50, by0 - 0.32 * img.height - j * 3, p)
            shadow_paste(im, img, x, y, off=8)
        d.rectangle((bx0, by0, bx0 + box_w, by0 + box_h), fill=(196, 150, 100))  # box front
        d.line((bx0, by0 + 6, bx0 + box_w, by0 + 6), fill=(170, 125, 80), width=8)
        lp = ease((tt - 0.62) / 0.15)
        if lp > 0:  # lid comes down
            ly = lerp(-200, by0 - 60, lp)
            d.rounded_rectangle((bx0 - 40, ly, bx0 + box_w + 40, ly + 110), 14, fill=(176, 130, 84))
            d.rectangle((bx0 - 40, ly + 110, bx0 + box_w + 40, by0 + box_h), fill=(188, 142, 94)) if lp >= 1 else None
            if lp >= 1:
                d.line((W / 2, by0 - 60, W / 2, by0 + box_h), fill=(225, 205, 160), width=60)  # tape
        sp = ease((tt - 0.82) / 0.08)
        if sp > 0:  # sticker
            r = int(lerp(220, 120, sp))
            cx, cy = W // 2, by0 + 190
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="white", outline=PINK, width=8)
            lg = logo.copy()
            lg.thumbnail((int(r * 1.3), int(r * 1.3)))
            im.paste(lg, (cx - lg.width // 2, cy - lg.height // 2), lg)
        caption(d, "STEP 4", "Packed & ready to ship", "across India", y=1410)
        footer(im, d, {})
        emit(im)

    if finale:
        unbox_and_read(emit, secs, logo, [marked_piece(f) for f in finale])

    # 5. end card
    end = end_frame("Shop our " + title, ["WhatsApp 95793 06816", "Search Flinosh Prints on Amazon"], end_foot)
    n = secs(3.6)
    for i in range(n):
        emit(end)
    proc.stdin.close()
    proc.wait()
    return count[0] / FPS


def marked_piece(path):
    im = Image.open(path).convert("RGBA")
    a = im.split()[3]
    im.alpha_composite(watermark(im.size))
    im.putalpha(a)
    return im


def draw_book(d, x, y, w, h, cover, spine):
    d.rectangle((x + 10, y - 22, x + w - 6, y + 4), fill=(246, 240, 226))  # page block seen from above
    for k in range(5):
        d.line((x + 14, y - 18 + k * 5, x + w - 10, y - 18 + k * 5), fill=(222, 214, 196), width=1)
    d.rounded_rectangle((x, y, x + w, y + h), 12, fill=cover)
    d.rectangle((x, y, x + 34, y + h), fill=spine)
    d.rectangle((x + 70, y + 90, x + w - 40, y + 96), fill=(235, 205, 120))
    d.rectangle((x + 70, y + h - 120, x + w - 40, y + h - 114), fill=(235, 205, 120))


def unbox_and_read(emit, secs, logo, marks):
    """The parcel opens, the bookmarks come out, then two slide into books."""
    box_w, box_h = 760, 420
    bx0, by0 = (W - box_w) // 2, 900
    m = len(marks)
    sc = 620 / max(mk.height for mk in marks)
    sm = [mk.resize((int(mk.width * sc), int(mk.height * sc)), Image.LANCZOS) for mk in marks]
    n = secs(3.4)
    for i in range(n):
        tt = i / n
        im, d = base((245, 238, 228))
        lp = ease(tt / 0.25)  # lid lifts away
        rise = ease((tt - 0.25) / 0.45)
        for j, mk in enumerate(sm):
            fx = W / 2 + (j - (m - 1) / 2) * (mk.width + 30)
            x = lerp(W / 2, fx, rise) - mk.width / 2
            y = lerp(by0 + 40, 230, rise)
            if rise > 0:
                shadow_paste(im, mk, x, y, off=12)
        d.rectangle((bx0, by0, bx0 + box_w, by0 + box_h), fill=(196, 150, 100))
        d.line((bx0, by0 + 6, bx0 + box_w, by0 + 6), fill=(170, 125, 80), width=8)
        if lp < 1:
            ly = lerp(by0 - 60, -260, lp)
            d.rounded_rectangle((bx0 - 40, ly, bx0 + box_w + 40, ly + 110), 14, fill=(176, 130, 84))
            lg = logo.copy()
            lg.thumbnail((90, 90))
            im.paste(lg, (W // 2 - lg.width // 2, int(ly + 10)), lg)
        caption(d, "STEP 5", "Open the parcel", "made fresh for your order", y=1440)
        footer(im, d, {})
        emit(im)

    # into the books: two books side by side, a bookmark slides into each
    books = [((120, 820, 400, 560), (128, 30, 44), (96, 20, 32)), ((560, 820, 400, 560), (30, 72, 60), (20, 52, 44))]
    pick = [sm[0], sm[min(1, m - 1)]] if m > 1 else [sm[0], sm[0]]
    n = secs(3.8)
    for i in range(n):
        tt = i / n
        im, d = base((236, 226, 210))
        d.rectangle((0, 1380, W, 1380), fill=(200, 185, 160))
        for k, ((x, y, w, h), cover, spine) in enumerate(books):
            mk = pick[k]
            p = ease((tt - 0.12 - k * 0.22) / 0.4)
            bm_x = x + w / 2 - mk.width / 2
            bm_y = lerp(-mk.height - 40, y - mk.height * 0.42, p)
            if p > 0:
                visible = mk.crop((0, 0, mk.width, max(1, int(min(mk.height, y + 4 - bm_y)))))
                shadow_paste(im, visible, bm_x, bm_y, off=8)
            draw_book(d, x, y, w, h, cover, spine)
        caption(d, "", "Slip it into your book", "and never lose your page", y=1450)
        footer(im, d, {})
        emit(im)


if __name__ == "__main__":
    out, sheet, boxes, title, product = sys.argv[1:6]
    finale = sys.argv[6].split(",") if len(sys.argv) > 6 and sys.argv[6] else None
    foot = sys.argv[7] if len(sys.argv) > 7 else "Designed & printed in Goa"
    print(out, build(out, sheet, json.loads(boxes), title, product, finale, foot), "s")
