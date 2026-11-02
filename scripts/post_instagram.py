#!/usr/bin/env python3
"""Publish the next due post from social/instagram-queue.json to Instagram.

Runs from .github/workflows/instagram.yml. Needs two repository secrets:
IG_USER_ID (the Instagram professional account id) and IG_ACCESS_TOKEN.
The token can come from "Instagram API with Instagram login" (starts with
IG, uses graph.instagram.com and is refreshed on every run so it doesn't
lapse) or from Facebook login (a Page token, uses graph.facebook.com).
Without them it does nothing.

Posts at most one entry per run: the oldest entry whose date (IST) is today
or earlier and that isn't yet in social/instagram-posted.json.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "social" / "instagram-queue.json"
POSTED = ROOT / "social" / "instagram-posted.json"
API = "https://graph.facebook.com/v21.0"
IG_API = "https://graph.instagram.com/v21.0"
IST = timezone(timedelta(hours=5, minutes=30))


def call(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram API error {e.code}: {e.read().decode()[:500]}")


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
    queue = json.loads(QUEUE.read_text())
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else []
    done = {p["key"] for p in posted}
    today = datetime.now(IST).date().isoformat()
    due = [p for p in sorted(queue, key=lambda p: p["date"])
           if p["date"] <= today and p["date"] + p["image"] not in done]
    if not due:
        print(f"Nothing due on {today}.")
        return
    post = due[0]
    container = call(f"{user}/media", {"image_url": post["image"], "caption": post["caption"],
                                       "access_token": token})["id"]
    for _ in range(12):
        if status(container, token) in ("FINISHED", None):
            break
        time.sleep(5)
    media = call(f"{user}/media_publish", {"creation_id": container, "access_token": token})["id"]
    posted.append({"key": post["date"] + post["image"], "media_id": media,
                   "posted_at": datetime.now(IST).isoformat(timespec="minutes")})
    POSTED.write_text(json.dumps(posted, indent=2) + "\n")
    print(f"Posted {post['image']} as {media}.")


if __name__ == "__main__":
    main()
