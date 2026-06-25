"""
Bexar County — procurement scraper.

Primary:   BidNetDirect / Texas Purchasing Group
           https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids
Fallback:  bexar.org/Bids.aspx (CivicEngage — blocks plain bot UA, needs browser headers)

BidNetDirect is the better source: Bexar posts all formal solicitations there,
and the public closed-bids page lists awarded contracts without requiring login.
"""
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)

# BidNetDirect public pages (no login needed for listings)
BIDNET_CLOSED  = "https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids"
BIDNET_OPEN    = "https://www.bidnetdirect.com/texas/bexar-county/solicitations/open-bids"

# Fallback
CIVICENGAGE    = "https://www.bexar.org/Bids.aspx"

# Headers that pass as a real browser
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class BexarScraper(BaseScraper):
    source_name = "bexar_county"

    def __init__(self):
        super().__init__()
        # Override session headers with browser-like values for this scraper
        self.session.headers.update(BROWSER_HEADERS)

    # ------------------------------------------------------------------
    # BidNetDirect (primary)
    # ------------------------------------------------------------------

    def _scrape_bidnet(self, url: str, label: str) -> list[dict]:
        logger.info(f"[bexar] Fetching BidNetDirect {label}...")
        resp = self.fetch(url)
        if not resp:
            return []

        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        # BidNetDirect bid rows: each bid is a <tr> or <li> with a title link
        # and metadata (agency, close date, bid number)
        for row in soup.select("tr, li.bid-item, .bid-row, [class*='solicitation']"):
            text = row.get_text(separator=" ", strip=True)
            if not text or len(text) < 10:
                continue

            hits = self.matches(text)
            if not hits:
                continue

            link  = row.find("a", href=True)
            title = link.get_text(strip=True) if link else text[:120]
            href  = link["href"] if link else ""
            url_  = (
                href if href.startswith("http")
                else urljoin("https://www.bidnetdirect.com", href)
            ) if href else url

            # Try to parse a dollar amount from the row
            amount = 0.0
            for m in re.findall(r"\$[\d,]+(?:\.\d{2})?", text):
                try:
                    amount = float(m.replace("$", "").replace(",", ""))
                    break
                except ValueError:
                    pass

            results.append({
                "source":           self.source_name,
                "title":            title[:300],
                "description":      text[:2000],
                "vendor":           "",
                "amount":           amount,
                "award_date":       "",
                "agency":           "Bexar County",
                "url":              url_,
                "matched_keywords": hits,
                "raw":              {"text": text[:500], "source_url": url},
            })

        return results

    # ------------------------------------------------------------------
    # CivicEngage fallback (bexar.org) with browser headers
    # ------------------------------------------------------------------

    def _scrape_civicengage(self) -> list[dict]:
        logger.info("[bexar] Trying CivicEngage fallback (bexar.org)...")
        resp = self.fetch(CIVICENGAGE)
        if not resp:
            logger.warning("[bexar] CivicEngage also blocked — Bexar source unavailable this run")
            return []

        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        for row in soup.select("table tr, .CivicSB-BidOpportunity, [class*='bid']"):
            text = row.get_text(separator=" ", strip=True)
            hits = self.matches(text)
            if not hits:
                continue

            link  = row.find("a", href=True)
            title = link.get_text(strip=True) if link else text[:100]
            url_  = urljoin("https://www.bexar.org", link["href"]) if link else CIVICENGAGE

            results.append({
                "source":           self.source_name,
                "title":            title[:300],
                "description":      text[:2000],
                "vendor":           "",
                "amount":           0.0,
                "award_date":       "",
                "agency":           "Bexar County",
                "url":              url_,
                "matched_keywords": hits,
                "raw":              {"text": text[:500]},
            })

        return results

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        results = []

        # Try BidNetDirect first (closed bids = awarded contracts)
        results.extend(self._scrape_bidnet(BIDNET_CLOSED, "closed bids"))
        results.extend(self._scrape_bidnet(BIDNET_OPEN,   "open bids"))

        # If BidNetDirect returned nothing, try CivicEngage with browser headers
        if not results:
            results.extend(self._scrape_civicengage())

        # Deduplicate by URL
        seen, unique = set(), []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)

        logger.info(f"[bexar] → {len(unique)} matching bids")
        return unique