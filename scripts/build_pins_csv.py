#!/usr/bin/env python3
"""Make a Pinterest bulk-upload CSV that schedules one pin per product and idea page.

Pinterest no longer auto-publishes from RSS, so this file is uploaded by hand in
Pinterest > Settings > Import content > Upload .csv. It also writes JPG copies of
the photos to assets/pins/ (Pinterest bulk upload does not take WebP); commit and
publish those before uploading the CSV.

    python3 scripts/build_pins_csv.py OUTPUT.csv [START_DATE] [BOARD]
"""
import csv
import datetime as dt
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_feeds import ROOT, SITE, cards, idea_pages  # noqa: E402

PRIORITY = ["diwali", "deepawali", "children", "return gift", "bookmark", "sticker", "tag", "card"]
SLOTS_UTC = [(3, 30), (13, 30)]  # 09:00 and 19:00 India time


def rank(item):
    text = (item["title"] + " " + item["description"]).lower()
    return next((i for i, word in enumerate(PRIORITY) if word in text), len(PRIORITY))


def to_jpg(image_url):
    rel = image_url[len(SITE):]
    src = ROOT / rel
    out = ROOT / "assets" / "pins" / (src.stem + ".jpg")
    if not out.exists():
        out.parent.mkdir(exist_ok=True)
        img = Image.open(src).convert("RGB")
        img.thumbnail((1000, 1500))
        img.save(out, "JPEG", quality=85, optimize=True)
    return SITE + out.relative_to(ROOT).as_posix()


def main():
    output = Path(sys.argv[1])
    start = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today() + dt.timedelta(days=1)
    board = sys.argv[3] if len(sys.argv) > 3 else "Flinosh Print Gifts"

    items = list(idea_pages()) + list(cards((ROOT / "index.html").read_text()))
    seen, unique = set(), []
    for it in sorted(items, key=rank):
        if it["image"] not in seen or it["link"].startswith(SITE + "ideas/"):
            seen.add(it["image"])
            unique.append(it)

    with output.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"])
        for n, it in enumerate(unique):
            day = start + dt.timedelta(days=n // len(SLOTS_UTC))
            hour, minute = SLOTS_UTC[n % len(SLOTS_UTC)]
            when = dt.datetime.combine(day, dt.time(hour, minute)).strftime("%Y-%m-%dT%H:%M:%S")
            title = it["title"] if " " in it["title"] else f"Personalised {it['title']} by Flinosh Prints"
            desc = f"{it['description']} Designed and printed by Flinosh Prints in Goa, delivered across India."
            w.writerow([title[:100], to_jpg(it["image"]), board, "", desc[:500], it["link"], when,
                        "personalised gifts, printed gifts India, Flinosh Prints"])
    print(f"{output}: {len(unique)} pins from {start} at 2 a day")


if __name__ == "__main__":
    main()
