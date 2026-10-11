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
        img = re.search(r'<img src="(assets/[^"]+)" alt="([^"]*)"', body)
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
        yield {
            "guid": SITE + img.group(1),
            "title": text(title.group(1)),
            "description": " ".join(parts),
            "image": SITE + img.group(1),
            "alt": html.unescape(img.group(2)),
            "link": link,
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
