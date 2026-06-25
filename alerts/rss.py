"""
RSS 2.0 feed generator.
Writes public/feed.xml — serve via GitHub Pages or any static host.

Subscribers can follow via any RSS reader (Feedly, NetNewsWire, etc.)
or pipe into IFTTT/Zapier for secondary alerts.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import config
import db

logger = logging.getLogger(__name__)


def _xml_escape(text: str) -> str:
    t = str(text or "")
    return (
        t.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )


def _to_rfc822(iso_str: str) -> str:
    """Convert ISO date string to RFC-822 for RSS pubDate."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(iso_str[:19], fmt[:len(iso_str)])
            return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except (ValueError, TypeError):
            pass
    return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")


def _build_item(record: dict) -> str:
    kw_list = json.loads(record.get("matched_keywords", "[]"))
    kw_str  = ", ".join(kw_list)

    amount_str = (
        f"${record['amount']:,.2f}" if record.get("amount") else "Amount not reported"
    )
    vendor_str  = record.get("vendor") or "Not listed"
    source_str  = record.get("source", "").upper().replace("_", " ")
    agency_str  = _xml_escape(record.get("agency", ""))
    title_str   = _xml_escape(record.get("title", ""))
    desc_raw    = record.get("description", "") or record.get("title", "")

    description_html = (
        f"&lt;p&gt;&lt;strong&gt;Source:&lt;/strong&gt; {source_str}&lt;/p&gt;"
        f"&lt;p&gt;&lt;strong&gt;Vendor:&lt;/strong&gt; {_xml_escape(vendor_str)}&lt;/p&gt;"
        f"&lt;p&gt;&lt;strong&gt;Agency:&lt;/strong&gt; {agency_str}&lt;/p&gt;"
        f"&lt;p&gt;&lt;strong&gt;Amount:&lt;/strong&gt; {amount_str}&lt;/p&gt;"
        f"&lt;p&gt;&lt;strong&gt;Keywords matched:&lt;/strong&gt; {_xml_escape(kw_str)}&lt;/p&gt;"
        f"&lt;p&gt;&lt;strong&gt;Description:&lt;/strong&gt; {_xml_escape(desc_raw[:500])}&lt;/p&gt;"
    )

    pub_date = _to_rfc822(record.get("award_date") or record.get("discovered_at", ""))

    return f"""    <item>
      <title>{title_str}</title>
      <link>{_xml_escape(record.get("url", ""))}</link>
      <description>{description_html}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{record.get("fingerprint", record.get("id", ""))}</guid>
      <category>{source_str}</category>
    </item>"""


def generate_feed(database) -> str:
    records  = db.get_recent(database, limit=100)
    now_rfc  = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items    = "\n".join(_build_item(r) for r in records)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{_xml_escape(config.SITE_TITLE)}</title>
    <link>{config.SITE_LINK}</link>
    <description>{_xml_escape(config.SITE_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{config.SITE_LINK}/feed.xml"
               rel="self" type="application/rss+xml"/>
{items}
  </channel>
</rss>"""


def write_feed(database) -> int:
    """
    Write the RSS feed to disk.
    Returns the number of new items marked as alerted.
    """
    out_path = Path(config.RSS_OUTPUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    feed = generate_feed(database)
    out_path.write_text(feed, encoding="utf-8")
    logger.info(f"[rss] Feed written → {out_path}  ({len(feed):,} bytes, {len(db.get_recent(database))} items)")

    # Mark pending items as alerted
    pending = db.get_unalerted(database, "rss")
    for r in pending:
        db.mark_alerted(database, r["id"], "rss")

    return len(pending)
