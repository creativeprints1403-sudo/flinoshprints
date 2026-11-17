#!/usr/bin/env python3
"""Publish the next due post from social/instagram-queue.json to Instagram.

Runs from .github/workflows/instagram.yml. Needs two repository secrets:
IG_USER_ID (the Instagram professional account id) and IG_ACCESS_TOKEN.
The token can come from "Instagram API with Instagram login" (starts with
IG, uses graph.instagram.com and is refreshed on every run so it doesn't
lapse) or from Facebook login (a Page token, uses graph.facebook.com).
Without them it does nothing.

Posts at most one entry per run: the oldest entry whose date (IST) is today
or up to STALE_DAYS earlier and that isn't yet in social/instagram-posted.json.
Older missed entries are skipped, since their order-by dates may have passed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Another account (e.g. AdCut) can use its own files via IG_DIR, e.g. "social/adcut".
DIR = ROOT / os.environ.get("IG_DIR", "social")
QUEUE = DIR / "instagram-queue.json"
POSTED = DIR / "instagram-posted.json"
PRODUCTS = DIR / "instagram-products.json"
API = "https://graph.facebook.com/v21.0"
IG_API = "https://graph.instagram.com/v21.0"
IST = timezone(timedelta(hours=5, minutes=30))
STALE_DAYS = 2


class ApiError(Exception):
    pass


def call(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise ApiError(f"Instagram API error {e.code}: {e.read().decode()[:500]}")


def status(container, token):
    q = urllib.parse.urlencode({"fields": "status_code", "access_token": token})
    with urllib.request.urlopen(f"{API}/{container}?{q}", timeout=60) as r:
        return json.load(r).get("status_code")


def check(user, token):
    """Fail early, with a clear message, if the id or token is wrong."""
    q = urllib.parse.urlencode({"fields": "username", "access_token": token})
    try:
        with urllib.request.urlopen(f"{API}/{user}?{q}", timeout=60) as r:
            print(f"Connected to Instagram as @{json.load(r).get('username')}.")
    except urllib.error.HTTPError as e:
        sys.exit(f"Can't reach the Instagram account ({e.code}): {e.read().decode()[:500]}")


def refresh(token):
    """Extend an Instagram-login token's 60-day life; failure isn't fatal."""
    q = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
    try:
        with urllib.request.urlopen(f"https://graph.instagram.com/refresh_access_token?{q}",
                                    timeout=60) as r:
            days = json.load(r).get("expires_in", 0) // 86400
            print(f"Token refreshed, valid for {days} more days.")
    except urllib.error.HTTPError as e:
        print(f"Token refresh failed ({e.code}); posting anyway.")


def media(entry):
    """The photo or video URL an entry posts (videos go out as Reels)."""
    return entry.get("video") or entry["image"]


def next_product(posted):
    """The product posted longest ago (never-posted first), skipping any
    photo that went out in the last 3 days."""
    if not PRODUCTS.exists():
        return None
    today = datetime.now(IST).date().isoformat()
    products = [p for p in json.loads(PRODUCTS.read_text()) if p.get("until", "9999") >= today]
    cutoff = (datetime.now(IST) - timedelta(days=3)).isoformat()
    recent = [p["key"] for p in posted if p["posted_at"] >= cutoff]
    last = {}
    for i, p in enumerate(posted):
        if p["key"].startswith("product:"):
            last[p["key"][8:]] = i
    fresh = [p for p in products if not any(k.endswith(media(p)) for k in recent)]
    if not fresh:
        return None
    return min(fresh, key=lambda p: last.get(media(p), -1))


def main():
    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not user or not token:
        print("IG_USER_ID / IG_ACCESS_TOKEN not set; skipping.")
        return
    global API
    if token.startswith("IG"):
        API = IG_API
        refresh(token)
    check(user, token)
    if os.environ.get("CHECK_ONLY") == "true":
        print("Check only; nothing posted.")
        return
    queue = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else []
    done = {p["key"] for p in posted}
    now = datetime.now(IST).date()
    today, oldest = now.isoformat(), (now - timedelta(days=STALE_DAYS)).isoformat()
    due = [p for p in sorted(queue, key=lambda p: p["date"])
           if oldest <= p["date"] <= today and p["date"] + media(p) not in done]
    for _ in range(3):  # a broken photo is logged and skipped, then the next one is tried
        if due:
            post = due.pop(0)
            key = post["date"] + media(post)
        else:
            post = next_product(posted)
            if not post:
                print(f"Nothing due on {today}.")
                return
            key = "product:" + media(post)
        stamp = datetime.now(IST).isoformat(timespec="minutes")
        try:
            media_id = publish(user, token, post)
        except (ApiError, KeyError) as e:
            print(f"Could not post {key}: {e}")
            posted.append({"key": key, "failed": True, "posted_at": stamp})
            POSTED.write_text(json.dumps(posted, indent=2) + "\n")
            continue
        posted.append({"key": key, "media_id": media_id, "posted_at": stamp})
        POSTED.write_text(json.dumps(posted, indent=2) + "\n")
        print(f"Posted {key} as {media_id}.")
        return
    sys.exit("Three posts in a row failed; see above.")


def publish(user, token, post):
    params = {"caption": post["caption"], "access_token": token}
    if post.get("video"):
        params.update(media_type="REELS", video_url=post["video"], share_to_feed="true")
    else:
        params["image_url"] = post["image"]
    container = call(f"{user}/media", params)["id"]
    for _ in range(60 if post.get("video") else 12):
        if status(container, token) in ("FINISHED", None):
            break
        time.sleep(5)
    return call(f"{user}/media_publish", {"creation_id": container, "access_token": token})["id"]


if __name__ == "__main__":
    main()
