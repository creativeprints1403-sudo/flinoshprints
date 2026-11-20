#!/usr/bin/env python3
"""Rebuild feed.xml (product RSS for Pinterest auto-publish) and sitemap.xml.

Run from the repository root after adding or changing product cards or idea pages:
    python3 scripts/build_feeds.py
"""
import datetime as dt
import html
import json
import re
import subprocess
import urllib.parse
from email.utils import format_datetime
from pathlib import Path

SITE = "https://flinoshprints.com/"
ROOT = Path(__file__).resolve().parent.parent
DATES = ROOT / "scripts" / "feed-dates.json"
TODAY = dt.date.today().isoformat()


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def cards(page):
    for m in re.finditer(r'<article class="(?:feature|product)[^"]*">(.*?)</article>', page, re.S):
        body = m.group(1)
        img = re.search(r'<img src="(assets/[^"]+|https://m\.media-amazon\.com/[^"]+)" alt="([^"]*)"', body)
        title = re.search(r"<h3>(.*?)</h3>", body, re.S)
        if not img or not title:
            continue
        spec = re.search(r'<p class="spec">(.*?)</p>', body, re.S)
        desc = re.search(r"<p>(.*?)</p>", body, re.S)
        btn = re.search(r'class="btn btn-primary" href="([^"]+)"', body)
        link = html.unescape(btn.group(1)) if btn and "amazon.in" in btn.group(1) else SITE + "#shop"
        parts = [text(spec.group(1)) + "."] if spec else []
        if desc:
            parts.append(text(desc.group(1)))
        src = img.group(1) if img.group(1).startswith("http") else SITE + img.group(1)
        yield {
            "guid": src,
            "title": text(title.group(1)),
            "description": " ".join(parts),
            "image": premium_card(src) or src,
            "alt": html.unescape(img.group(2)),
            "link": link,
        }


STORE = "https://www.amazon.in/s?me=A27RXOS2FK94TR&k="
SKIP = ("friends",)  # copyrighted designs stay off Pinterest


def stem(url):
    """Amazon image id or file name, e.g. 81TG2+Oz3yL._SL800_.jpg -> 81TG2-Oz3yL."""
    return Path(url).name.split(".")[0].replace("+", "-")


def premium_card(url):
    """The watermarked premium card made for Instagram, when there is one."""
    card = ROOT / "assets" / "ig" / (stem(url) + ".jpg")
    return SITE + card.relative_to(ROOT).as_posix() if card.exists() else None


def amazon_products(have):
    """Amazon listings from social/instagram-products.json that the site cards
    don't already cover, pinned with their premium card and linked to Amazon."""
    path = ROOT / "social" / "instagram-products.json"
    if not path.exists():
        return
    for p in json.loads(path.read_text()):
        if p.get("video") or not p.get("card") or not p.get("title"):
            continue
        if any(w in p["title"].lower() for w in SKIP) or stem(p["card"]) in have:
            continue
        asin = re.search(r"/dp/([A-Z0-9]{10})", p.get("amazon", ""))
        if asin and asin.group(1) in have:
            continue
        have.add(stem(p["card"]))
        if asin:
            have.add(asin.group(1))
        feats = " · ".join(p.get("features", []))
        desc = f"{p['title']} by Flinosh Prints. {feats}." + (f" For {p['use']}." if p.get("use") else "")
        yield {
            "guid": SITE + p["card"],
            "title": f"{p['title']} | Flinosh Prints on Amazon",
            "description": desc + " Designed in Goa, delivered across India.",
            "image": SITE + p["card"],
            "alt": f"{p['title']} by Flinosh Prints",
            "link": p["amazon"] if asin else STORE + urllib.parse.quote_plus(p["title"]),
        }


def amazon_listings(have):
    """The rest of the Amazon catalogue from social/amazon-listings.json, pinned
    with the Amazon photo and linked to the product page. Each listing has a
    "from" date so new pins trickle out a few a day instead of all at once."""
    path = ROOT / "social" / "amazon-listings.json"
    if not path.exists():
        return
    for p in json.loads(path.read_text()):
        if p["from"] > TODAY or p["asin"] in have or any(w in p["title"].lower() for w in SKIP):
            continue
        have.add(p["asin"])
        yield {
            "guid": "https://www.amazon.in/dp/" + p["asin"],
            "title": f"{p['title']} | Flinosh Prints on Amazon",
            "description": f"{p['title']} by Flinosh Prints. Designed in Goa, delivered across India. Order on Amazon.in.",
            "image": p["image"],
            "alt": f"{p['title']} by Flinosh Prints",
            "link": "https://www.amazon.in/dp/" + p["asin"],
        }


def idea_pages():
    for path in sorted((ROOT / "ideas").glob("*.html")):
        page = path.read_text()
        title = re.search(r"<title>(.*?)</title>", page, re.S)
        desc = re.search(r'<meta name="description" content="([^"]*)"', page)
        img = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        url = SITE + path.relative_to(ROOT).as_posix()
        yield {
            "guid": url,
            "title": text(title.group(1)).split(" | ")[0],
            "description": html.unescape(desc.group(1)) if desc else "",
            "image": img.group(1),
            "alt": text(title.group(1)).split(" | ")[0],
            "link": url,
        }


def lastmod(rel):
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return TODAY if dirty or not out else out


def pin_image(url):
    """Prefer the JPG copy in assets/pins/ (Pinterest handles JPG best)."""
    jpg = ROOT / "assets" / "pins" / (Path(url).stem + ".jpg")
    return SITE + jpg.relative_to(ROOT).as_posix() if jpg.exists() else url


def esc(s):
    return html.escape(s, quote=True)


def main():
    index = (ROOT / "index.html").read_text()
    items = list(idea_pages()) + list(cards(index))
    have = set()
    for it in items:
        have.add(stem(it["guid"]))
        have.update(re.findall(r"/dp/([A-Z0-9]{10})", it["link"]))
    items += list(amazon_products(have))
    items += list(amazon_listings(have))
    seen = json.loads(DATES.read_text()) if DATES.exists() else {}
    for it in items:
        seen.setdefault(it["guid"], TODAY)
    DATES.write_text(json.dumps(seen, indent=2, sort_keys=True) + "\n")

    items.sort(key=lambda it: seen[it["guid"]], reverse=True)
    rows = []
    for it in items:
        it["image"] = pin_image(it["image"])
        when = dt.datetime.fromisoformat(seen[it["guid"]]).replace(hour=9, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
        rows.append(f"""  <item>
    <title>{esc(it['title'])}</title>
    <link>{esc(it['link'])}</link>
    <guid isPermaLink="false">{esc(it['guid'])}</guid>
    <pubDate>{format_datetime(when)}</pubDate>
    <description>{esc(it['description'])}</description>
    <enclosure url="{esc(it['image'])}" type="image/{'jpeg' if it['image'].endswith('.jpg') else 'webp'}" length="0"/>
    <media:content url="{esc(it['image'])}" medium="image"><media:description>{esc(it['alt'])}</media:description></media:content>
  </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Flinosh Prints: cards, tags, bookmarks and invitations</title>
  <link>{SITE}</link>
  <atom:link href="{SITE}feed.xml" rel="self" type="application/rss+xml"/>
  <description>Printed cards, gift tags, bookmarks, stickers and invitations, designed in Goa and delivered across India.</description>
  <language>en-IN</language>
{chr(10).join(rows)}
</channel>
</rss>
"""
    (ROOT / "feed.xml").write_text(feed)

    pages = ["index.html"] + [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "ideas").glob("*.html"))]
    urls = []
    for rel in pages:
        loc = SITE if rel == "index.html" else SITE + rel
        urls.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod(rel)}</lastmod>\n  </url>")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n")
    print(f"feed.xml: {len(items)} items; sitemap.xml: {len(urls)} pages")


if __name__ == "__main__":
    main()
