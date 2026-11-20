"""Cartoon 'AI for Kids' Shorts: Bolt the robot and Momo the owl.

Usage: python3 scripts/make_kids_shorts.py scripts/kids-episodes.json out_dir [episode_id ...]
Needs Outfit-Bold/Regular and Noto Color Emoji fonts (paths below).
Renders 1080x1920 30fps mp4 with a synth music bed and talk blips.
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT = "/mnt/skills/examples/canvas-design/canvas-fonts/Outfit-Bold.ttf"
FONT_R = "/mnt/skills/examples/canvas-design/canvas-fonts/Outfit-Regular.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
NAVY = (20, 34, 64)
ORANGE = (255, 159, 28)

def font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_R, size)

_emoji_cache = {}
def emoji(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new("RGBA", (220, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        s = size / max(im.size)
        _emoji_cache[key] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return _emoji_cache[key]

# ---------------------------------------------------------------- characters
SS = 3  # supersample factor for smooth edges

def robot(eyes="open", mouth="smile"):
    w, h = 420 * SS, 520 * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = SS
    teal, teal_d = (38, 198, 218), (22, 150, 170)
    # antenna
    d.line([(210 * s, 40 * s), (210 * s, 95 * s)], fill=(90, 100, 120), width=10 * s)
    d.ellipse([186 * s, 8 * s, 234 * s, 56 * s], fill=(255, 214, 60), outline=(230, 170, 20), width=4 * s)
    # head
    d.rounded_rectangle([40 * s, 90 * s, 380 * s, 330 * s], radius=70 * s, fill=teal, outline=teal_d, width=8 * s)
    # ears
    d.rounded_rectangle([14 * s, 170 * s, 50 * s, 250 * s], radius=14 * s, fill=teal_d)
    d.rounded_rectangle([370 * s, 170 * s, 406 * s, 250 * s], radius=14 * s, fill=teal_d)
    # face screen
    d.rounded_rectangle([78 * s, 128 * s, 342 * s, 296 * s], radius=50 * s, fill=(24, 36, 66))
    glow = (120, 245, 255)
    if eyes == "open":
        for cx in (160, 260):
            d.ellipse([(cx - 26) * s, 168 * s, (cx + 26) * s, 230 * s], fill=glow)
            d.ellipse([(cx - 6) * s, 178 * s, (cx + 10) * s, 196 * s], fill=(255, 255, 255))
    else:
        for cx in (160, 260):
            d.arc([(cx - 28) * s, 180 * s, (cx + 28) * s, 225 * s], 200, 340, fill=glow, width=10 * s)
    # cheeks
    for cx in (118, 302):
        d.ellipse([(cx - 16) * s, 232 * s, (cx + 16) * s, 252 * s], fill=(255, 120, 150))
    if mouth == "open":
        d.ellipse([186 * s, 238 * s, 234 * s, 278 * s], fill=glow)
    else:
        d.arc([180 * s, 222 * s, 240 * s, 268 * s], 20, 160, fill=glow, width=9 * s)
    # neck + body
    d.rectangle([180 * s, 328 * s, 240 * s, 350 * s], fill=(90, 100, 120))
    d.rounded_rectangle([100 * s, 345 * s, 320 * s, 500 * s], radius=50 * s, fill=teal, outline=teal_d, width=8 * s)
    # chest heart light
    hx, hy = 210 * s, 420 * s
    r = 16 * s
    d.ellipse([hx - 2 * r, hy - r - r // 2, hx, hy + r // 2], fill=(255, 90, 120))
    d.ellipse([hx, hy - r - r // 2, hx + 2 * r, hy + r // 2], fill=(255, 90, 120))
    d.polygon([(hx - 2 * r + 2 * s, hy), (hx + 2 * r - 2 * s, hy), (hx, hy + 2 * r)], fill=(255, 90, 120))
    # arms
    d.rounded_rectangle([60 * s, 370 * s, 105 * s, 460 * s], radius=22 * s, fill=teal_d)
    d.rounded_rectangle([315 * s, 370 * s, 360 * s, 460 * s], radius=22 * s, fill=teal_d)
    return im.resize((w // SS, h // SS), Image.LANCZOS)

def owl(eyes="open", mouth="closed"):
    w, h = 420 * SS, 520 * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = SS
    body, body_d, belly = (150, 105, 200), (115, 75, 165), (235, 215, 250)
    # ear tufts
    d.polygon([(95 * s, 150 * s), (120 * s, 40 * s), (180 * s, 120 * s)], fill=body_d)
    d.polygon([(325 * s, 150 * s), (300 * s, 40 * s), (240 * s, 120 * s)], fill=body_d)
    # body
    d.ellipse([60 * s, 80 * s, 360 * s, 500 * s], fill=body, outline=body_d, width=8 * s)
    d.ellipse([120 * s, 270 * s, 300 * s, 480 * s], fill=belly)
    for i, y in enumerate((320, 370, 420)):
        for x in (170, 210, 250)[: 3 - (i == 2)]:
            xx = x + (20 if i == 2 else 0)
            d.arc([(xx - 16) * s, (y - 10) * s, (xx + 16) * s, (y + 14) * s], 20, 160, fill=(200, 175, 230), width=5 * s)
    # wings
    d.ellipse([30 * s, 240 * s, 110 * s, 420 * s], fill=body_d)
    d.ellipse([310 * s, 240 * s, 390 * s, 420 * s], fill=body_d)
    # eyes
    for cx in (155, 265):
        d.ellipse([(cx - 58) * s, 130 * s, (cx + 58) * s, 246 * s], fill=(255, 255, 255), outline=(255, 200, 80), width=8 * s)
        if eyes == "open":
            d.ellipse([(cx - 28) * s, 160 * s, (cx + 28) * s, 216 * s], fill=(30, 30, 50))
            d.ellipse([(cx - 14) * s, 168 * s, (cx + 2) * s, 184 * s], fill=(255, 255, 255))
        else:
            d.arc([(cx - 32) * s, 165 * s, (cx + 32) * s, 210 * s], 200, 340, fill=(30, 30, 50), width=9 * s)
    # beak
    if mouth == "open":
        d.polygon([(190 * s, 236 * s), (230 * s, 236 * s), (210 * s, 262 * s)], fill=(255, 150, 40))
        d.polygon([(195 * s, 268 * s), (225 * s, 268 * s), (210 * s, 285 * s)], fill=(230, 120, 30))
    else:
        d.polygon([(190 * s, 236 * s), (230 * s, 236 * s), (210 * s, 275 * s)], fill=(255, 150, 40))
    # feet
    for cx in (170, 250):
        for dx in (-16, 0, 16):
            d.ellipse([(cx + dx - 10) * s, 488 * s, (cx + dx + 10) * s, 512 * s], fill=(255, 150, 40))
    return im.resize((w // SS, h // SS), Image.LANCZOS)

SPRITES = {}
def sprite(who, eyes, mouth):
    key = (who, eyes, mouth)
    if key not in SPRITES:
        SPRITES[key] = (robot if who == "bolt" else owl)(eyes, mouth)
    return SPRITES[key]

# ---------------------------------------------------------------- logo
def logo(size=150):
    s = 4
    S = size * s
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=NAVY)
    d.ellipse([S * 0.1, S * 0.1, S * 0.9, S * 0.9], outline=ORANGE, width=int(S * 0.06))
    c = S / 2
    d.line([(c, c), (c, S * 0.24)], fill=(255, 255, 255), width=int(S * 0.06))
    d.line([(c, c), (S * 0.7, c)], fill=(255, 255, 255), width=int(S * 0.06))
    d.ellipse([c - S * 0.05, c - S * 0.05, c + S * 0.05, c + S * 0.05], fill=ORANGE)
    # spark
    px, py, r = S * 0.76, S * 0.26, S * 0.12
    d.polygon([(px, py - r), (px + r * 0.3, py - r * 0.3), (px + r, py), (px + r * 0.3, py + r * 0.3),
               (px, py + r), (px - r * 0.3, py + r * 0.3), (px - r, py), (px - r * 0.3, py - r * 0.3)], fill=(255, 214, 60))
    return im.resize((size, size), Image.LANCZOS)

# ---------------------------------------------------------------- background
def background(seed):
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([140, 210, 255]), np.array([255, 236, 210])
    grad = (top * (1 - y) + bot * y)
    arr = np.repeat(grad[:, None, :], W, axis=1).reshape(H, W, 3).astype(np.uint8)
    im = Image.fromarray(arr).convert("RGBA")
    d = ImageDraw.Draw(im)
    # hills
    d.ellipse([-300, 1560, 700, 2300], fill=(120, 205, 120))
    d.ellipse([380, 1600, 1400, 2300], fill=(100, 190, 110))
    d.rectangle([0, 1760, W, H], fill=(100, 190, 110))
    # soft clouds (kept clear of the panels)
    for cx, cy in ((-40, 400), (930, 380)):
        for dx, dy, r in ((0, 0, 50), (55, -18, 60), (115, 0, 45)):
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255, 170))
    return im

def rounded(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)

def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if f.getlength(t) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines

def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

# ---------------------------------------------------------------- props
def draw_prop(frame, prop, t):
    """prop: {"items": ["🐱", ...], "labels": [...], "marks": ["✅"...]}"""
    panel = (90, 470, 990, 1000)
    d = ImageDraw.Draw(frame)
    rounded(d, panel, 50, fill=(255, 255, 255, 235), outline=(255, 255, 255), width=6)
    items = prop.get("items", [])
    labels = prop.get("labels", [])
    marks = prop.get("marks", [])
    n = max(1, len(items))
    size = {1: 300, 2: 250, 3: 210, 4: 170}.get(n, 140)
    gap = (panel[2] - panel[0]) / n
    cy = 700 if labels or marks else 735
    for i, ch in enumerate(items):
        k = ease_out_back(t * 3 - i * 0.35)
        if k <= 0.01:
            continue
        if ch.startswith("@"):
            sp = sprite(ch[1:], "open", "smile" if ch == "@bolt" else "closed")
            sc = size * 1.25 * k / sp.height
            em = sp.resize((max(1, int(sp.width * sc)), max(1, int(sp.height * sc))), Image.LANCZOS)
        else:
            em = emoji(ch, max(4, int(size * k)))
        cx = panel[0] + gap * (i + 0.5)
        frame.alpha_composite(em, (int(cx - em.width / 2), int(cy - em.height / 2)))
        if i < len(marks) and marks[i] and t * 3 - i * 0.35 > 1.2:
            mk = emoji(marks[i], 90)
            frame.alpha_composite(mk, (int(cx + size * 0.25), int(cy + size * 0.15)))
        if i < len(labels) and labels[i] and k > 0.6:
            f = font(54)
            tw = f.getlength(labels[i])
            d.text((cx - tw / 2, cy + size / 2 + 40), labels[i], font=f, fill=NAVY)

# ---------------------------------------------------------------- bubble
def draw_bubble(frame, who, text, reveal):
    d = ImageDraw.Draw(frame)
    f = font(66)
    box = (70, 1040, 1010, 1290)
    color = (255, 255, 255)
    edge = (38, 198, 218) if who == "bolt" else (150, 105, 200)
    rounded(d, box, 46, fill=color, outline=edge, width=8)
    tx = 260 if who == "bolt" else 820
    d.polygon([(tx - 40, box[3] - 4), (tx + 40, box[3] - 4), (tx + (-30 if who == "bolt" else 30), box[3] + 70)], fill=color)
    d.line([(tx - 40, box[3]), (tx + (-30 if who == "bolt" else 30), box[3] + 70), (tx + 40, box[3])], fill=edge, width=8)
    name = "BOLT" if who == "bolt" else "MOMO"
    nf = font(40)
    nw = nf.getlength(name) + 50
    nx = box[0] + 40 if who == "bolt" else box[2] - 40 - nw
    rounded(d, (nx, box[1] - 30, nx + nw, box[1] + 30), 30, fill=edge)
    d.text((nx + 25, box[1] - 25), name, font=nf, fill=(255, 255, 255))
    lines = wrap(text, f, box[2] - box[0] - 90)
    total = len(text)
    shown = int(total * reveal)
    count = 0
    lh = 78
    y0 = (box[1] + box[3]) / 2 - lh * len(lines) / 2 + 4
    for i, line in enumerate(lines):
        part = line[: max(0, shown - count)]
        count += len(line) + 1
        lw = f.getlength(line)
        d.text(((box[0] + box[2]) / 2 - lw / 2, y0 + i * lh), part, font=f, fill=NAVY)

# ---------------------------------------------------------------- render
def render(ep, out_dir):
    beats = ep["beats"]
    bg = background(hash(ep["id"]) % 1000)
    lg = logo(120)
    wm_font = font(40)
    title_f = font(84)
    tag_f = font(38)
    frames_dir = os.path.join(out_dir, "_frames_" + ep["id"])
    os.makedirs(frames_dir, exist_ok=True)
    timeline, t0 = [], 0.0
    for b in beats:
        timeline.append((t0, b))
        t0 += b.get("dur", 3.6)
    end_card = 2.6
    total = t0 + end_card
    nframes = int(total * FPS)
    blips = []  # (time, who)
    for start, b in timeline:
        if b["who"] in ("bolt", "momo"):
            words = len(b["say"].split())
            span = b.get("dur", 3.6) * 0.55
            for i in range(words):
                blips.append((start + 0.1 + span * i / max(1, words), b["who"]))
    for fi in range(nframes):
        t = fi / FPS
        frame = bg.copy()
        d = ImageDraw.Draw(frame)
        # header
        frame.alpha_composite(lg, (50, 60))
        d.text((186, 78), "Hours Saved by AI", font=wm_font, fill=NAVY)
        d.text((186, 124), ep.get("series", "AI for Kids"), font=tag_f, fill=(230, 120, 0))
        lines = wrap(ep["title"], title_f, 960)
        for i, line in enumerate(lines[:2]):
            lw = title_f.getlength(line)
            d.text((W / 2 - lw / 2 + 4, 250 + i * 96 + 4), line, font=title_f, fill=(255, 255, 255, 180))
            d.text((W / 2 - lw / 2, 250 + i * 96), line, font=title_f, fill=NAVY)
        cur = None
        for start, b in timeline:
            if start <= t:
                cur = (start, b)
        speaker = None
        if t < t0 and cur:
            start, b = cur
            dur = b.get("dur", 3.6)
            lt = (t - start) / dur
            draw_prop(frame, b.get("prop", {"items": ep.get("icon", ["🤖"])}), (t - start) / 1.2)
            speaker = b["who"]
            draw_bubble(frame, b["who"], b["say"], min(1, lt / 0.55))
        else:
            # end card
            et = (t - t0) / end_card
            draw_prop(frame, {"items": ["@bolt", "@momo"], "labels": ["Bolt", "Momo"]}, et * 2)
            panel = (70, 1040, 1010, 1290)
            rounded(d, panel, 46, fill=(255, 159, 28))
            f = font(70)
            for i, line in enumerate(["Follow for more", ep.get("end", "fun learning!")]):
                lw = f.getlength(line)
                d.text((W / 2 - lw / 2, 1080 + i * 86), line, font=f, fill=(255, 255, 255))
        # characters
        for who, x in (("bolt", 50), ("momo", 610)):
            phase = 0 if who == "bolt" else 1.7
            talking = speaker == who and cur and (t - cur[0]) < cur[1].get("dur", 3.6) * 0.6
            bob = math.sin(t * (6 if talking else 2.2) + phase) * (14 if talking else 8)
            blink = (t + phase) % 3.4 < 0.13
            mouth = ("open" if int(t * 8) % 2 == 0 else "closed") if talking else ("smile" if who == "bolt" else "closed")
            sp = sprite(who, "closed" if blink else "open", mouth)
            scale = 0.9
            spr = sp.resize((int(sp.width * scale), int(sp.height * scale)), Image.BILINEAR)
            frame.alpha_composite(spr, (x, int(1395 + bob)))
        # watermark
        wm = "hours saved by ai"
        d.text((W - 60 - font(34, False).getlength(wm), H - 70), wm, font=font(34, False), fill=(255, 255, 255, 200))
        frame.convert("RGB").save(os.path.join(frames_dir, f"{fi:05d}.png"), compress_level=1)
    wav = os.path.join(out_dir, f"_{ep['id']}.wav")
    make_audio(wav, total, blips, ep.get("seed", 1))
    out = os.path.join(out_dir, f"{ep['id']}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "%05d.png"),
                    "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    subprocess.run(["rm", "-rf", frames_dir, wav])
    print("wrote", out, f"{total:.1f}s")

# ---------------------------------------------------------------- audio
SR = 44100
def tone(freq, dur, kind="sine", vol=0.2):
    t = np.arange(int(SR * dur)) / SR
    if kind == "square":
        w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5
    elif kind == "tri":
        w = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    else:
        w = np.sin(2 * np.pi * freq * t)
    env = np.minimum(1, t / 0.01) * np.exp(-t * 6)
    return w * env * vol

def make_audio(path, total, blips, seed):
    n = int(SR * (total + 0.5))
    mix = np.zeros(n)
    # cheerful I-V-vi-IV in C, plucky arpeggio + bass
    chords = [[261.6, 329.6, 392.0], [196.0, 246.9, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 349.2]]
    beat = 60 / 112
    i = 0
    tpos = 0.0
    while tpos < total:
        ch = chords[(i // 8) % 4]
        note = ch[[0, 1, 2, 1][i % 4]] * 2
        s = int(tpos * SR)
        tn = tone(note, beat * 0.9, "tri", 0.07)
        mix[s:s + len(tn)] += tn[: max(0, n - s)]
        if i % 4 == 0:
            b = tone(ch[0] / 2, beat * 1.8, "sine", 0.14)
            mix[s:s + len(b)] += b[: max(0, n - s)]
        if i % 2 == 1:
            hat = np.random.default_rng(i).normal(0, 1, int(SR * 0.03)) * np.exp(-np.arange(int(SR * 0.03)) / 200) * 0.025
            mix[s:s + len(hat)] += hat[: max(0, n - s)]
        i += 1
        tpos = i * beat / 2
    rng = np.random.default_rng(seed)
    for bt, who in blips:
        base = 880 if who == "bolt" else 520
        f = base * rng.uniform(0.85, 1.25)
        bl = tone(f, 0.07, "square" if who == "bolt" else "sine", 0.08)
        s = int(bt * SR)
        mix[s:s + len(bl)] += bl[: max(0, n - s)]
    fade = int(SR * 1.0)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.clip(mix, -1, 1)
    data = (mix * 32000).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())

if __name__ == "__main__":
    eps = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    want = set(sys.argv[3:])
    for ep in eps:
        if not want or ep["id"] in want:
            render(ep, out)
    logo(512).save(os.path.join(out, "hours-saved-logo.png"))
    for who in ("bolt", "momo"):
        sprite(who, "open", "smile" if who == "bolt" else "closed").save(os.path.join(out, f"{who}.png"))
