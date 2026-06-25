"""
Discord webhook alert.
Posts a formatted embed to a Discord channel for each new surveillance contract.

Setup:
  1. Discord server → channel settings → Integrations → Webhooks → New Webhook
  2. Copy URL → DISCORD_WEBHOOK_URL env var
"""
import json
import logging
import time

import requests

import config
import db

logger = logging.getLogger(__name__)

# Source → color mapping for Discord embeds
SOURCE_COLORS = {
    "usaspending":   0x5865F2,   # blurple — federal
    "cosa_awards":   0xEB459E,   # fuchsia — SA municipal
    "esbd":          0xFEE75C,   # yellow  — Texas state
    "bexar_county":  0x57F287,   # green   — county
}
DEFAULT_COLOR = 0xED4245  # red fallback


def _amount_str(amount: float | None) -> str:
    if amount and amount > 0:
        return f"${amount:,.2f}"
    return "Not reported"


def _build_embed(record: dict) -> dict:
    kw_list  = json.loads(record.get("matched_keywords", "[]"))
    source   = record.get("source", "unknown")
    color    = SOURCE_COLORS.get(source, DEFAULT_COLOR)

    fields = [
        {"name": "🏢 Vendor",    "value": record.get("vendor") or "Not listed",  "inline": True},
        {"name": "💰 Amount",    "value": _amount_str(record.get("amount")),      "inline": True},
        {"name": "🏛️ Agency",   "value": record.get("agency") or "Unknown",      "inline": True},
        {"name": "📅 Date",      "value": record.get("award_date") or "Unknown",  "inline": True},
        {"name": "🔍 Source",    "value": source.upper().replace("_", " "),       "inline": True},
        {"name": "🎯 Keywords",  "value": ", ".join(kw_list[:6]) or "—",         "inline": False},
    ]

    desc = record.get("description", "")
    if desc and len(desc) > 300:
        desc = desc[:297] + "..."

    return {
        "title":       (record.get("title") or "Surveillance Contract")[:256],
        "description": desc,
        "url":         record.get("url", ""),
        "color":       color,
        "fields":      fields,
        "footer": {
            "text": "Texas Surveillance Contract Watch • txsurveillancewatch.github.io"
        },
    }


def send_alert(record: dict) -> bool:
    """
    Send a single award as a Discord embed.
    Returns True on success.
    """
    if not config.DISCORD_WEBHOOK_URL:
        logger.debug("[discord] No webhook URL configured — skipping")
        return False

    payload = {
        "username":   "TX Surveillance Watch",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Texas_flag_map.svg/240px-Texas_flag_map.svg.png",
        "embeds":     [_build_embed(record)],
    }

    try:
        resp = requests.post(
            config.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 429:
            # Rate-limited — back off and retry once
            retry_after = resp.json().get("retry_after", 5)
            logger.warning(f"[discord] Rate limited — waiting {retry_after}s")
            time.sleep(retry_after + 0.5)
            resp = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=15)

        resp.raise_for_status()
        logger.info(f"[discord] ✓ Sent: {record.get('title', '')[:60]}")
        return True

    except requests.RequestException as e:
        logger.error(f"[discord] Failed: {e}")
        return False


def send_pending(database) -> int:
    """
    Send all un-alerted awards to Discord.
    Returns number of successfully sent alerts.
    """
    if not config.DISCORD_WEBHOOK_URL:
        return 0

    pending = db.get_unalerted(database, "discord")
    sent = 0

    for record in pending:
        if send_alert(record):
            db.mark_alerted(database, record["id"], "discord")
            sent += 1
        time.sleep(1)  # respect Discord rate limit (5 webhooks/sec per URL)

    if sent:
        logger.info(f"[discord] Sent {sent} alert(s)")
    return sent


def send_startup_ping(database) -> None:
    """Optional: send a status embed when the watcher starts."""
    if not config.DISCORD_WEBHOOK_URL:
        return

    s = db.stats(database)
    payload = {
        "username": "TX Surveillance Watch",
        "embeds": [{
            "title":       "🟢 Watcher Online",
            "description": f"Monitoring {len(config.PORTALS)} procurement portals across Texas.",
            "color":       0x57F287,
            "fields": [
                {"name": "Total records",  "value": str(s["total_awards"]), "inline": True},
                {"name": "Last run",
                 "value": (s.get("last_run") or {}).get("finished_at", "Never")[:16],
                 "inline": True},
            ],
        }],
    }
    try:
        requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception:
        pass
