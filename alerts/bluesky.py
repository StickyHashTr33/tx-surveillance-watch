"""
Bluesky bot poster.
Uses the atproto library to post surveillance contract alerts as
short-form posts to a Bluesky account.

Setup:
  1. Create a Bluesky account at bsky.app (e.g., txsurveillancewatch.bsky.social)
  2. Settings → App Passwords → Generate password
  3. Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD env vars

Install: pip install atproto
"""
import json
import logging
import time

import config
import db

logger = logging.getLogger(__name__)

MAX_POST_CHARS = 300


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _build_post_text(record: dict) -> str:
    """
    Build a 300-char Bluesky post.
    Format:
        🚨 [SOURCE] New surveillance contract in Texas
        Vendor: X  |  $YYY,YYY
        Agency: Z
        Keywords: license plate recognition, Flock Safety
        → link
    """
    source   = record.get("source", "").upper().replace("_", " ")
    vendor   = record.get("vendor") or "Unknown vendor"
    agency   = record.get("agency") or "Unknown agency"
    amount   = record.get("amount")
    kw_list  = json.loads(record.get("matched_keywords", "[]"))
    url      = record.get("url", "")

    amount_str = f"${amount:,.0f}" if amount else "amount TBD"
    kw_str     = ", ".join(kw_list[:3])

    text = (
        f"🚨 [{source}] Surveillance tech contract in Texas\n"
        f"Vendor: {vendor} | {amount_str}\n"
        f"Agency: {agency}\n"
        f"Tags: {kw_str}\n"
        f"→ {url}"
    )
    return _truncate(text, MAX_POST_CHARS)


def post_alert(record: dict) -> bool:
    """
    Post a single award alert to Bluesky.
    Returns True on success.
    """
    if not config.BLUESKY_HANDLE or not config.BLUESKY_PASSWORD:
        logger.debug("[bluesky] Credentials not configured — skipping")
        return False

    try:
        from atproto import Client
    except ImportError:
        logger.error("[bluesky] atproto not installed. Run: pip install atproto")
        return False

    text = _build_post_text(record)

    try:
        client = Client()
        client.login(config.BLUESKY_HANDLE, config.BLUESKY_PASSWORD)
        client.send_post(text=text)
        logger.info(f"[bluesky] ✓ Posted: {record.get('title', '')[:50]}")
        return True
    except Exception as e:
        logger.error(f"[bluesky] Failed: {e}")
        return False


def post_pending(database) -> int:
    """
    Post all un-alerted awards to Bluesky.
    Returns number successfully posted.
    """
    if not (config.BLUESKY_HANDLE and config.BLUESKY_PASSWORD):
        return 0

    pending = db.get_unalerted(database, "bluesky")
    posted = 0

    for record in pending:
        if post_alert(record):
            db.mark_alerted(database, record["id"], "bluesky")
            posted += 1
        time.sleep(2)  # avoid rate limits

    if posted:
        logger.info(f"[bluesky] Posted {posted} alert(s)")
    return posted
