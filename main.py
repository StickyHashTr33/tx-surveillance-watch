"""
TxSurveillanceWatch — main entry point.

Usage:
    python main.py              # run once immediately
    python main.py --loop       # run every N hours (set SCRAPE_INTERVAL_HOURS)
    python main.py --stats      # print DB stats and exit
    python main.py --source usaspending   # run a single scraper
"""
import argparse
import logging
import sys
import time
from datetime import datetime

import config
import db
from scrapers import USASpendingScraper, COSAScraper, ESBDScraper, BexarScraper
from alerts import write_feed, send_pending, send_startup_ping, post_pending

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Scraper registry
# ---------------------------------------------------------------------------
SCRAPERS = {
    "usaspending": (USASpendingScraper, config.ENABLE_USASPENDING),
    "cosa":        (COSAScraper,        config.ENABLE_COSA),
    "esbd":        (ESBDScraper,        config.ENABLE_ESBD),
    "bexar":       (BexarScraper,       config.ENABLE_BEXAR),
}


# ---------------------------------------------------------------------------
# Core run logic
# ---------------------------------------------------------------------------

def run_scraper(scraper_cls, database) -> tuple[int, int]:
    """
    Instantiate and run a single scraper class.
    Returns (new_awards, total_fetched).
    """
    scraper = scraper_cls()
    source  = scraper.source_name
    started = datetime.utcnow().isoformat()
    new     = 0
    total   = 0

    try:
        records = scraper.scrape()
        total   = len(records)

        for record in records:
            if db.insert_award(database, record):
                new += 1
                logger.info(
                    f"  ✚ NEW [{source}] {record.get('title', '')[:70]} "
                    f"| {record.get('vendor', '')} | keywords={record.get('matched_keywords', [])}"
                )

        db.log_run(database, source, started, "ok", new)
        logger.info(f"[{source}] Done — {new} new / {total} total fetched")

    except Exception as e:
        logger.exception(f"[{source}] Scraper error: {e}")
        db.log_run(database, source, started, "error", 0, str(e))

    return new, total


def run_all(database, source_filter: str | None = None) -> int:
    """
    Run all enabled scrapers (or just the one matching source_filter).
    Returns total new awards found.
    """
    total_new = 0

    for name, (cls, enabled) in SCRAPERS.items():
        if source_filter and name != source_filter:
            continue
        if not enabled and not source_filter:
            logger.info(f"[{name}] Disabled in config — skipping")
            continue

        logger.info(f"━━━ Running scraper: {name} ━━━")
        new, _ = run_scraper(cls, database)
        total_new += new

    return total_new


def run_alerts(database):
    """Push new awards through all configured alert channels."""
    n_rss     = write_feed(database)
    n_discord = send_pending(database)
    n_bluesky = post_pending(database)
    logger.info(
        f"Alerts — RSS: {n_rss} items, Discord: {n_discord} sent, Bluesky: {n_bluesky} posted"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Texas Surveillance Contract Watch — procurement scraper"
    )
    parser.add_argument(
        "--loop", action="store_true",
        help=f"Run continuously every {config.SCRAPE_INTERVAL_HOURS}h"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print DB statistics and exit"
    )
    parser.add_argument(
        "--source", choices=list(SCRAPERS.keys()),
        help="Run only this scraper"
    )
    parser.add_argument(
        "--no-alerts", action="store_true",
        help="Scrape but skip alert delivery"
    )
    args = parser.parse_args()

    # Init DB
    database = db.get_db()
    db.init_db(database)

    # Stats mode
    if args.stats:
        s = db.stats(database)
        print(f"\n=== {config.SITE_TITLE} — Database Stats ===")
        print(f"Total awards:  {s['total_awards']}")
        print("By source:")
        for src, cnt in (s.get("by_source") or {}).items():
            print(f"  {src:<20} {cnt}")
        if s.get("last_run"):
            lr = s["last_run"]
            print(f"Last run:      {lr.get('source')} @ {lr.get('finished_at')} — {lr.get('status')}")
        print()
        return

    # Startup ping
    send_startup_ping(database)

    if args.loop:
        logger.info(f"Starting loop — interval: {config.SCRAPE_INTERVAL_HOURS}h")
        while True:
            logger.info(f"=== Scrape cycle start @ {datetime.utcnow().isoformat()} ===")
            total_new = run_all(database, source_filter=args.source)

            if total_new > 0 and not args.no_alerts:
                run_alerts(database)
            elif total_new == 0:
                logger.info("No new awards — writing RSS anyway")
                write_feed(database)

            sleep_secs = config.SCRAPE_INTERVAL_HOURS * 3600
            logger.info(f"Sleeping {config.SCRAPE_INTERVAL_HOURS}h until next cycle…")
            time.sleep(sleep_secs)
    else:
        # Single run
        logger.info(f"=== Single run @ {datetime.utcnow().isoformat()} ===")
        total_new = run_all(database, source_filter=args.source)

        if not args.no_alerts:
            run_alerts(database)

        logger.info(f"=== Done — {total_new} new awards found ===")


if __name__ == "__main__":
    main()
