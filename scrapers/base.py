"""
Base scraper — all source-specific scrapers inherit from this.
"""
import time
import logging

import requests

import config
import keywords

logger = logging.getLogger(__name__)


class BaseScraper:
    source_name: str = "base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        })

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def fetch(self, url: str, **kwargs) -> requests.Response | None:
        try:
            time.sleep(config.REQUEST_DELAY_SECONDS)
            resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.error(f"[{self.source_name}] GET {url} → {e}")
            return None

    def post(self, url: str, **kwargs) -> requests.Response | None:
        try:
            time.sleep(config.REQUEST_DELAY_SECONDS)
            resp = self.session.post(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.error(f"[{self.source_name}] POST {url} → {e}")
            return None

    # ------------------------------------------------------------------
    # Keyword matching
    # ------------------------------------------------------------------

    def matches(self, *fields: str) -> list[str]:
        """Scan one or more text fields; return deduplicated keyword hits."""
        return keywords.matches(*fields)

    # ------------------------------------------------------------------
    # Override in subclass
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        """
        Return a list of award dicts with keys:
            source, title, description, vendor, amount (float),
            award_date (ISO str), agency, url, matched_keywords (list), raw (dict)
        """
        raise NotImplementedError
