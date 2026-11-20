"""Render text-only viral-style Shorts for the Hours Saved by Ai channel.

Each Short: a 2-second punch hook, the problem, the exact prompt typed out,
the result, and a follow call. 1080x1920, 30 fps, with a synth beat.
Usage: python3 scripts/make_viral_shorts.py [slug ...]
"""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
NAVY, AMBER, WHITE, BOX = (19, 34, 64), (255, 170, 20), (255, 255, 255), (10, 18, 36)
GREEN = (60, 210, 120)
F = "/usr/share/fonts/opentype/inter/"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
OUT = Path("assets/youtube")

SHORTS = [
    ("inbox-30-seconds", "STOP|reading every email.", "50 unread emails. No time.",
     "Summarise these emails. List only what I must do, who it's for, and the deadline.",
     "A 5-line to-do list instead of 50 emails."),
    ("meeting-notes", "YOUR|meeting notes are useless.", "Pages of notes. Zero next steps.",
     "Turn these notes into action items: owner, task, due date. Table format.",
     "Clear action table, ready to share."),
    ("polite-no", "SAY|no without guilt.", "Someone wants a favour you can't do.",
     "Write a warm, short email saying no to this request and offer one alternative.",
     "Kind, firm reply in 10 seconds."),
    ("excel-messy-names", "FIX|messy names in 1 formula.", "  rAHUL   sharma  ...in 500 rows.",
     "Give me an Excel formula to trim spaces and fix capitals in A2.",
     "=PROPER(TRIM(A2))  then drag down."),
    ("long-pdf", "DON'T|read the whole PDF.", "40 pages. You need 5 facts.",
     "Summarise this document in 5 bullet points. Then list any numbers or dates.",
     "The 5 points that matter, in seconds."),
    ("plan-your-week", "PLAN|your whole week in 1 prompt.", "Too many tasks. No plan.",
     "Here are my tasks and deadlines. Build a Mon-Fri plan, hardest work in the mornings.",
     "A week plan you can follow today."),
    ("ask-me-questions", "THIS|one line fixes bad AI answers.", "Generic answers? Add this to any prompt:",
     "Before you answer, ask me 3 questions to understand what I need.",
     "Answers that fit you, not everyone."),
    ("reply-templates", "NEVER|type the same reply twice.", "Same customer questions, every day.",
     "Write 5 short reply templates for my most common customer questions: price, delivery, refunds.",
     "Copy, paste, send. Done."),
    ("excel-split-names", "SPLIT|full names instantly.", "First and last name stuck in one cell?",
     "Excel formula to split the full name in A2 into first and last name.",
     "=TEXTSPLIT(A2, \" \")  in Excel 365."),
]

def font(name, size):
    return ImageFont.truetype(name if name.startswith("/") else F + name, size)

def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split(" "):
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt) <= width or not line:
            line = test
        else:
            lines.append(line); line = word
    return lines + [line]

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

# scene timings (seconds)
HOOK, PROB, PROMPT, RESULT, CTA = 2.2, 2.6, 6.0, 3.2, 2.5
TOTAL = HOOK + PROB + PROMPT + RESULT + CTA

def frame(t, spec):
    _, hook, problem, prompt, result = spec
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    # progress bar keeps people watching
    d.rectangle([0, 0, int(W * t / TOTAL), 14], fill=AMBER)
    d.text((60, H - 110), "HOURS SAVED BY AI", font=font("Inter-ExtraBold.otf", 34), fill=(150, 165, 195))
    x = 80
    if t < HOOK:
        first, rest = hook.split("|")
        s = 0.6 + 0.4 * ease(t / 0.35) + 0.04 * math.sin(t * 9) * (t > 0.35)
        big = font("InterDisplay-Black.otf", int(170 * s))
        lines = [first] + wrap(d, rest.upper(), font("InterDisplay-Black.otf", 150), W - 160)
        y = 560
        for i, ln in enumerate(lines):
            f = big if i == 0 else font("InterDisplay-Black.otf", 140)
            if i and t < 0.25 + i * 0.12:
                continue
            d.text((x, y), ln, font=f, fill=AMBER if i == 0 else WHITE)
            y += f.size + 20
        return img
    t -= HOOK
    if t < PROB:
        f = font("InterDisplay-ExtraBold.otf", 96)
        y = 700 + int(60 * (1 - ease(t / 0.4)))
        for ln in wrap(d, problem, f, W - 160):
            d.text((x, y), ln, font=f, fill=WHITE); y += 120
        return img
    t -= PROB
    if t < PROMPT:
        d.text((x, 520), "Paste this into ChatGPT:", font=font("InterDisplay-ExtraBold.otf", 72), fill=AMBER)
        mf = font(MONO, 54)
        shown = prompt[: int(len(prompt) * min(1, t / (PROMPT * 0.7)))]
        lines = wrap(d, prompt, mf, W - 240)
        d.rounded_rectangle([60, 640, W - 60, 640 + 80 + 72 * len(lines)], 28, fill=BOX)
        y, left = 680, len(shown)
        for ln in lines:
            part = ln[:max(0, left)]
            d.text((110, y), part, font=mf, fill=WHITE)
            left -= len(ln) + 1; y += 72
        if int(t * 3) % 2 == 0 and len(shown) < len(prompt):
            d.text((110 + d.textlength(part, font=mf), y - 72), "|", font=mf, fill=AMBER)
        return img
    t -= PROMPT
    if t < RESULT:
        a = ease(t / 0.4)
        d.text((x, 620), "Result:", font=font("InterDisplay-ExtraBold.otf", 80), fill=GREEN)
        mono = result.startswith("=")
        f = font(MONO, 76) if mono else font("InterDisplay-Black.otf", 104)
        y = 760 + int(50 * (1 - a))
        for ln in wrap(d, result, f, W - 160):
            d.text((x, y), ln, font=f, fill=AMBER if mono else WHITE); y += f.size + 26
        return img
    t -= RESULT
    f = font("InterDisplay-Black.otf", 120)
    s = 1 + 0.03 * math.sin(t * 6)
    y = 640
    for i, ln in enumerate(["That's", "hours", "saved."]):
        d.text((x, y), ln, font=font("InterDisplay-Black.otf", int(130 * s)), fill=AMBER if i == 1 else WHITE)
        y += 160
    d.text((x, y + 60), "Follow for one every day.", font=font("InterDisplay-ExtraBold.otf", 70), fill=WHITE)
    return img

def beat(path, seconds):
    sr = 44100
    n = int(sr * seconds)
    t = np.arange(n) / sr
    out = np.zeros(n)
    bpm = 118
    step = 60 / bpm
    for k in range(int(seconds / step) + 1):
        s = int(k * step * sr)
        L = min(int(0.25 * sr), n - s)
        if L <= 0: break
        tt = np.arange(L) / sr
        kick = np.sin(2 * np.pi * (55 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
        out[s:s + L] += 0.9 * kick
        if k % 2:  # off-beat hat
            h = min(int(0.05 * sr), n - s - int(step * sr / 2))
            if h > 0:
                hs = s + int(step * sr / 2)
                out[hs:hs + h] += 0.12 * np.random.randn(h) * np.exp(-np.arange(h) / sr * 80)
    chords = [(220, 277.2, 329.6), (196, 246.9, 293.7), (174.6, 220, 261.6), (196, 246.9, 293.7)]
    bar = step * 4
    for i, ch in enumerate(chords * 10):
        s, e = int(i * bar * sr), int((i + 1) * bar * sr)
        if s >= n: break
        e = min(e, n); tt = t[s:e] - t[s]
        env = np.minimum(1, tt * 4) * np.exp(-tt * 0.6)
        out[s:e] += 0.08 * env * sum(np.sin(2 * np.pi * f * tt) for f in ch)
    fade = np.minimum(1, (n - np.arange(n)) / (sr * 0.8))
    out = out * fade / max(1e-9, np.abs(out).max()) * 0.7
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())

def render(spec):
    slug = spec[0]
    OUT.mkdir(parents=True, exist_ok=True)
    wav = Path(f"/tmp/beat-{slug}.wav")
    beat(wav, TOTAL)
    dst = OUT / f"viral-{slug}.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
                          "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(dst)],
                         stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        p.stdin.write(frame(i / FPS, spec).tobytes())
    p.stdin.close(); p.wait()
    wav.unlink()
    print(dst)

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for spec in SHORTS:
        if not want or spec[0] in want:
            render(spec)
