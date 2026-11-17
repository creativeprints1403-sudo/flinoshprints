"""Make a 9:16 Instagram Reel (1080x1920 MP4) from product photos.

Each scene is a photo on a soft background with a headline, shown with a slow
zoom, followed by an end card saying how to order. Needs Pillow and ffmpeg.

    python3 scripts/make_reel.py wedding OUTPUT.mp4
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
SANS_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INK, PINK, GOLD = (52, 36, 24), (224, 26, 130), (176, 132, 52)

# (photo, crop box or None, headline, subline, background)
REELS = {
    "wedding": {
        "scenes": [
            ("assets/pins/template-gold-butterfly-wedding-invite.jpg", (0, 110, 1000, 930),
             "Wedding invitations", "with your names, date and venue", (250, 244, 233)),
            ("assets/pins/template-floral-animated-e-invite.jpg", (0, 110, 1000, 930),
             "Printed or for WhatsApp", "animated e-invites, lilac or blush", (240, 234, 248)),
            ("assets/envelope-pink-moroccan-trellis.webp", None,
             "Matching shagun envelopes", "5 gold-pattern designs", (251, 238, 242)),
            ("assets/floral-thank-you-stickers.webp", None,
             "Thank-you stickers", "for favours and return gifts", (246, 240, 232)),
        ],
        "end": ("Order your wedding set",
                ["WhatsApp 95793 06816", "flinoshprints.com"],
                "Designed in Goa · delivered across India"),
    },
}
SCENE_S, END_S, FADE_S = 3.2, 3.6, 0.5


def font(path, size):
    return ImageFont.truetype(path, size)


def centred(draw, y, text, f, fill):
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=fill)


def scene_frame(photo, headline, subline, bg, zoom):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    centred(d, 210, headline, font(SERIF, 76 if len(headline) < 22 else 64), INK)
    centred(d, 320, subline, font(SANS, 44), GOLD)
    box_w = int(940 * zoom)
    ph = photo.resize((box_w, int(photo.height * box_w / photo.width)), Image.LANCZOS)
    if ph.height > 1180 * zoom:
        ph = ph.resize((int(ph.width * 1180 * zoom / ph.height), int(1180 * zoom)), Image.LANCZOS)
    im.paste(ph, ((W - ph.width) // 2, 460 + (1200 - ph.height) // 2))
    logo = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    logo.thumbnail((84, 84))
    im.paste(logo, (W // 2 - 230, 1740), logo)
    d.text((W // 2 - 130, 1752), "flinoshprints", font=font(SANS_BOLD, 46), fill=INK)
    return im


def end_frame(title, lines, foot):
    im = Image.new("RGB", (W, H), (252, 247, 240))
    d = ImageDraw.Draw(im)
    logo = Image.open(ROOT / "assets" / "logo-mark.webp").convert("RGBA")
    logo.thumbnail((220, 220))
    im.paste(logo, ((W - logo.width) // 2, 430), logo)
    centred(d, 760, title, font(SERIF, 78), INK)
    y = 920
    for i, line in enumerate(lines):
        f = font(SANS_BOLD, 64 if i == 0 else 52)
        tw = d.textlength(line, font=f)
        if i == 0:
            d.rounded_rectangle(((W - tw) / 2 - 50, y - 24, (W + tw) / 2 + 50, y + 100), 62, fill=PINK)
            d.text(((W - tw) / 2, y), line, font=f, fill="white")
        else:
            d.text(((W - tw) / 2, y + 30), line, font=f, fill=INK)
        y += 170
    centred(d, y + 60, foot, font(SANS, 40), GOLD)
    return im


def main():
    name, out = sys.argv[1], Path(sys.argv[2])
    reel = REELS[name]
    frames = []
    for path, crop, head, sub, bg in reel["scenes"]:
        photo = Image.open(ROOT / path).convert("RGB")
        if crop:
            photo = photo.crop(crop)
        n = int(SCENE_S * FPS)
        frames.append([scene_frame(photo, head, sub, bg, 1 + 0.06 * i / n) for i in range(n)])
    end = end_frame(*reel["end"])
    frames.append([end] * int(END_S * FPS))
    fade = int(FADE_S * FPS)
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        for s, scene in enumerate(frames):
            for i, fr in enumerate(scene):
                if s + 1 < len(frames) and i >= len(scene) - fade:
                    t = (i - (len(scene) - fade) + 1) / fade
                    fr = Image.blend(fr, frames[s + 1][0], t)
                fr.save(f"{tmp}/{k:05d}.jpg", quality=92)
                k += 1
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", f"{tmp}/%05d.jpg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-crf", "23", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart",
                        str(out)], check=True)
    print(f"{out}: {k / FPS:.1f}s")


if __name__ == "__main__":
    main()
