"""Make 9:16 photos for AdCut videos with the Flinosh logo and watermark.

AdCut fills a 9:16 frame from each photo, so 4:5 photos lose their edges
(and the corner logo). These frames are already 1080x1920, with the
product centred, the faint watermark across it and the logo at the top.

    python3 scripts/make_adcut_frames.py out_dir photo1 [photo2 ...]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_post_cards import watermark  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
LOGO = Image.open(ROOT / "assets/logo-mark.webp").convert("RGBA")
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def frame(src):
    bg = Image.new("RGB", (W, H), (255, 255, 255))
    im = Image.open(src).convert("RGB")
    r = min(W * 0.94 / im.width, H * 0.70 / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (W - im.width) // 2, (H - im.height) // 2 + 30
    bg.paste(im, (x, y))
    wm = watermark(im.size)
    bg.paste(wm, (x, y), wm)
    logo = LOGO.copy()
    logo.thumbnail((150, 150))
    bg.paste(logo, ((W - logo.width) // 2, 110), logo)
    d = ImageDraw.Draw(bg)
    f = ImageFont.truetype(SERIF, 46)
    t = "Flinosh Prints"
    d.text(((W - d.textlength(t, font=f)) / 2, 110 + logo.height + 14), t, font=f, fill=(90, 60, 35))
    return bg


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(sys.argv[2:], 1):
        frame(p).save(out / f"{i}-{Path(p).stem}.jpg", quality=90)
