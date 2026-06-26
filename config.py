"""
Central config. All settings read from environment vars with sane defaults.
Copy .env.example → .env and fill in secrets.
"""
import os

# ---------------------------------------------------------------------------
# Output / alert targets
# ---------------------------------------------------------------------------
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
BLUESKY_HANDLE     = os.getenv("BLUESKY_HANDLE", "")      # e.g. txsurveillancewatch.bsky.social
BLUESKY_PASSWORD   = os.getenv("BLUESKY_APP_PASSWORD", "")  # App password, NOT account password

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DB_PATH          = os.getenv("DB_PATH", "watchdog.db")
RSS_OUTPUT_PATH  = os.getenv("RSS_OUTPUT_PATH", "public/feed.xml")
LOG_PATH         = os.getenv("LOG_PATH", "watchdog.log")

# ---------------------------------------------------------------------------
# Public site metadata (used in RSS + Bluesky posts)
# ---------------------------------------------------------------------------
SITE_TITLE       = "Texas Surveillance Contract Watch"
SITE_LINK        = os.getenv("SITE_LINK", "https://txsurveillancewatch.github.io")
SITE_DESCRIPTION = (
    "Automated public alerts for surveillance tech procurement contracts "
    "awarded by Texas municipalities, counties, and state agencies."
)

# ---------------------------------------------------------------------------
# HTTP / scraper behavior
# ---------------------------------------------------------------------------
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY", "2.0"))  # polite delay between requests
REQUEST_TIMEOUT       = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT = (
    "TxSurveillanceWatch/0.1 (public interest research; "
    "open source; +https://github.com/YOUR_HANDLE/tx-surveillance-watch)"
)

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "12"))

# ---------------------------------------------------------------------------
# Scraper enable flags  (set to "0" to disable a source)
# ---------------------------------------------------------------------------
ENABLE_USASPENDING = os.getenv("ENABLE_USASPENDING", "1") == "1"
ENABLE_COSA        = os.getenv("ENABLE_COSA", "1") == "1"
ENABLE_ESBD        = os.getenv("ENABLE_ESBD", "1") == "1"
ENABLE_BEXAR       = os.getenv("ENABLE_BEXAR", "1") == "1"
ENABLE_AUSTIN 	   = os.getenv("ENABLE_AUSTIN", "1") == "1"
ENABLE_LEGISTAR    = os.getenv("ENABLE_LEGISTAR", "1") == "1"

# ---------------------------------------------------------------------------
# USAspending-specific
# ---------------------------------------------------------------------------
USASPENDING_LOOKBACK_DAYS = int(os.getenv("USASPENDING_LOOKBACK_DAYS", "90"))

# ---------------------------------------------------------------------------
# Portal URLs  (for reference / testing)
# ---------------------------------------------------------------------------
PORTALS = {
    "cosa_awards": "https://webapp1.sanantonio.gov/TabulationsAwards/",
    "esbd":        "https://www.txsmartbuy.gov/esbd",
    "esbd_awards": "https://www.txsmartbuy.gov/esbdawards",
    "bexar":       "https://www.bexar.org/Bids.aspx",
    "usaspending": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
}
