#!/usr/bin/env python3
"""Post the Flinosh queue and product rotation to Threads.

Runs from .github/workflows/threads.yml with the secret THREADS_ACCESS_TOKEN
(THREADS_USER_ID is optional) (a long-lived Threads token from the "Flinosh autopost"
Meta app). Without them it does nothing. Uses the same queue, products and
premium cards as Instagram, with its own log in social/threads-posted.json.
Threads allows 500 characters, so hashtag lines are dropped and long captions
are cut at a sentence.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import post_instagram as ig

API = "https://graph.threads.net/v1.0"
ig.POSTED = ig.DIR / "threads-posted.json"


def get(path, **params):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{API}/{path}?{q}", timeout=60) as r:
        return json.load(r)


def post(path, params):
    req = urllib.request.Request(f"{API}/{path}", data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise ig.ApiError(f"Threads API error {e.code}: {e.read().decode()[:500]}")


STORE = "https://www.amazon.in/s?me=A27RXOS2FK94TR"
WHATSAPP = "https://wa.me/919579306816"


def links(entry):
    """A clickable Amazon link (the listing, or a search in the Flinosh store)
    and a WhatsApp chat link with a ready-made order message."""
    title = entry.get("title")
    amazon = entry.get("amazon") or (
        STORE + "&" + urllib.parse.urlencode({"k": title}) if title else STORE)
    hello = f"Hi Flinosh Prints, I'd like to order: {title}" if title else "Hi Flinosh Prints, I'd like to order"
    wa = WHATSAPP + "?" + urllib.parse.urlencode({"text": hello}, quote_via=urllib.parse.quote)
    return f"🛒 Buy on Amazon: {amazon}\n💬 Order on WhatsApp: {wa}\n🌐 More designs: https://flinoshprints.com"


def text(entry):
    """The caption's own words (no hashtags or Instagram 'link in bio' line)
    plus the two links, within Threads' 500 characters."""
    keep = [l for l in entry["caption"].split("\n")
            if not l.strip().startswith("#") and "link in bio" not in l and "WhatsApp 95793" not in l]
    body, tail = "\n".join(keep).strip(), links(entry)
    room = 500 - len(tail) - 2
    if len(body) > room:
        cut = body[: room - 1]
        body = cut[: max(cut.rfind(". "), cut.rfind("\n"), room // 2) + 1].strip()
    return f"{body}\n\n{tail}"


def publish(user, token, entry):
    params = {"text": text(entry), "access_token": token}
    if entry.get("video"):
        params.update(media_type="VIDEO", video_url=entry["video"])
    else:
        card = entry.get("card")
        params.update(media_type="IMAGE",
                      image_url=(ig.SITE + card) if card and (ig.ROOT / card).exists() else entry["image"])
    container = post(f"{user}/threads", params)["id"]
    for _ in range(60 if entry.get("video") else 12):
        time.sleep(5)
        try:
            state = get(container, fields="status", access_token=token).get("status")
        except urllib.error.HTTPError:
            state = None
        if state in ("FINISHED", None):
            break
        if state == "ERROR":
            raise ig.ApiError("Threads could not process the media.")
    return post(f"{user}/threads_publish", {"creation_id": container, "access_token": token})["id"]


def main():
    user, token = os.environ.get("THREADS_USER_ID") or "me", os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        print("THREADS_ACCESS_TOKEN not set; skipping.")
        return
    try:
        print(f"Connected to Threads as @{get(user, fields='username', access_token=token).get('username')}.")
        days = get("refresh_access_token", grant_type="th_refresh_token",
                   access_token=token).get("expires_in", 0) // 86400
        print(f"Token valid for {days} more days.")
    except urllib.error.HTTPError as e:
        sys.exit(f"Can't reach the Threads account ({e.code}): {e.read().decode()[:500]}")
    if os.environ.get("CHECK_ONLY") == "true":
        print("Check only; nothing posted.")
        return
    queue = json.loads(ig.QUEUE.read_text()) if ig.QUEUE.exists() else []
    posted = json.loads(ig.POSTED.read_text()) if ig.POSTED.exists() else []
    if not ig.slot_due(posted):
        return
    done = {p["key"] for p in posted}
    now = datetime.now(ig.IST).date()
    today, oldest = now.isoformat(), (now - timedelta(days=ig.STALE_DAYS)).isoformat()
    due = [p for p in sorted(queue, key=lambda p: p["date"])
           if oldest <= p["date"] <= today and p["date"] + ig.media(p) not in done]
    for _ in range(3):
        if due:
            entry = due.pop(0)
            key = entry["date"] + ig.media(entry)
        else:
            entry = ig.next_product(posted)
            if not entry:
                print(f"Nothing due on {today}.")
                return
            key = "product:" + ig.media(entry)
        stamp = datetime.now(ig.IST).isoformat(timespec="minutes")
        try:
            media_id = publish(user, token, entry)
        except (ig.ApiError, KeyError) as e:
            print(f"Could not post {key}: {e}")
            posted.append({"key": key, "failed": True, "posted_at": stamp})
            ig.POSTED.write_text(json.dumps(posted, indent=2) + "\n")
            continue
        posted.append({"key": key, "media_id": media_id, "posted_at": stamp})
        ig.POSTED.write_text(json.dumps(posted, indent=2) + "\n")
        print(f"Posted {key} as {media_id}.")
        return
    sys.exit("Three posts in a row failed; see above.")


if __name__ == "__main__":
    main()
