"""Upload the next due video in social/youtube-queue.json to YouTube.

Runs from .github/workflows/youtube.yml. Needs three repository secrets:
YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN (an OAuth refresh token
for the channel, with the youtube.upload scope). Without them it does nothing.

Queue entries: {"date": "YYYY-MM-DD", "video": "assets/reels/x.mp4" or URL,
"title": "...", "description": "...", "tags": [...], "privacy": "public",
optional "category" (YouTube category id, default "22") and "thumbnail" (a JPG/PNG
path; custom thumbnails need a phone-verified channel)}.
Uploaded entries are logged in social/youtube-posted.json.

Note: until Google audits the Cloud project, YouTube locks API uploads to
private, whatever "privacy" says; the channel owner can then make them public.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "social" / "youtube-queue.json"
POSTED = ROOT / "social" / "youtube-posted.json"
IST = timezone(timedelta(hours=5, minutes=30))


def token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=60) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Could not get a YouTube access token ({e.code}): {e.read().decode()[:300]}")


def channel(access):
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            items = json.load(r).get("items", [])
    except urllib.error.HTTPError as e:
        # an upload-only token (youtube.upload scope) can't read channel details
        return f"(name not readable with upload-only access, {e.code}; the token itself works)"
    return items[0]["snippet"]["title"] if items else "(no channel)"


def video_bytes(src):
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=120) as r:
            return r.read()
    return (ROOT / src).read_bytes()


def upload(access, entry):
    meta = {"snippet": {"title": entry["title"][:100], "description": entry.get("description", ""),
                        "tags": entry.get("tags", []), "categoryId": entry.get("category", "22")},
            "status": {"privacyStatus": entry.get("privacy", "public"), "selfDeclaredMadeForKids": False}}
    data = video_bytes(entry["video"])
    start = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))})
    with urllib.request.urlopen(start, timeout=60) as r:
        location = r.headers["Location"]
    put = urllib.request.Request(location, data=data, method="PUT",
                                 headers={"Content-Type": "video/mp4", "Content-Length": str(len(data))})
    with urllib.request.urlopen(put, timeout=600) as r:
        return json.load(r)


def set_thumbnail(access, video_id, path):
    data = (ROOT / path).read_bytes()
    kind = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
        data=data, method="POST", headers={"Authorization": f"Bearer {access}", "Content-Type": kind})
    try:
        with urllib.request.urlopen(req, timeout=120):
            return True
    except urllib.error.HTTPError as e:
        print(f"Thumbnail not set ({e.code}): {e.read().decode()[:300]}")
        return False


def main():
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("YouTube secrets not set; skipping.")
        return
    access = token()
    print(f"Connected to YouTube channel: {channel(access)}")
    if os.environ.get("CHECK_ONLY") == "true":
        print("Check only; nothing uploaded.")
        return
    queue = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else []
    done = {p["key"] for p in posted}
    today = datetime.now(IST).date()
    # Dates only set the order: each run uploads the next video not yet up, so a
    # missed day just shifts the queue. YT_PER_DAY caps uploads per IST day
    # (YouTube's default API quota allows about 6).
    per_day = int(os.environ.get("YT_PER_DAY") or 3)
    made = sum(1 for p in posted if not p.get("failed") and p["posted_at"].startswith(today.isoformat()))
    if made >= per_day:
        print(f"Already uploaded {made} today.")
        return
    due = [e for e in sorted(queue, key=lambda e: e["date"]) if e["date"] + e["video"] not in done]
    if not due:
        print(f"Nothing due on {today}.")
        return
    entry = due[0]
    key = entry["date"] + entry["video"]
    stamp = datetime.now(IST).isoformat(timespec="minutes")
    try:
        result = upload(access, entry)
    except urllib.error.HTTPError as e:
        posted.append({"key": key, "failed": True, "posted_at": stamp})
        POSTED.write_text(json.dumps(posted, indent=2) + "\n")
        sys.exit(f"Upload failed ({e.code}): {e.read().decode()[:500]}")
    status = result.get("status", {}).get("privacyStatus")
    record = {"key": key, "video_id": result["id"], "privacy": status, "posted_at": stamp}
    if entry.get("thumbnail"):
        record["thumbnail_set"] = set_thumbnail(access, result["id"], entry["thumbnail"])
    posted.append(record)
    POSTED.write_text(json.dumps(posted, indent=2) + "\n")
    print(f"Uploaded {entry['video']} as https://youtu.be/{result['id']} ({status}).")


if __name__ == "__main__":
    main()
