"""
Bexar County — procurement scraper.

Primary:   BidNetDirect / Texas Purchasing Group
           https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids
Fallback:  bexar.org/Bids.aspx (CivicEngage — selector: .bidsTbl / .bidItems)

Diagnostic confirmed:
  - BidNetDirect: 2,554 closed solicitations, plain <tr> rows, no JS needed
    Row format: "[SOL-NUM] [Title] [State] Calendar Published [date] Clock Closed Bid [date]"
  - CivicEngage: classes .bidsTbl and .bidItems are the real containers
"""
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)

BIDNET_CLOSED = "https://www.bidnetdirect.com/texas/bexar-county/solicitations/closed-bids"
BIDNET_OPEN   = "https://www.bidnetdirect.com/texas/bexar-county/solicitations/open-bids"
CIVICENGAGE   = "https://www.bexar.org/Bids.aspx"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection":      "keep-alive",
}

# BidNetDirect row noise — strip these before keyword matching
# so "Calendar Published 07/09/2025 Clock Closed Bid 07/25/2025" doesn't muddy hits
BIDNET_NOISE = re.compile(
    r"(Calendar\s+Published|Clock\s+Closed\s+Bid|Texas\s+Calendar|\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

# Solicitation number pattern — rows that start with this are real bids
SOL_NUM_RE = re.compile(r"^[A-Z]{2,5}[-_]\w{2,}-?\w+", re.IGNORECASE)


class BexarScraper(BaseScraper):
    source_name = "bexar_county"

    def __init__(self):
        super().__init__()
        self.session.headers.update(BROWSER_HEADERS)

    # ------------------------------------------------------------------
    # BidNetDirect
    # ------------------------------------------------------------------

    def _parse_bidnet_row(self, row, source_url: str) -> dict | None:
        """
        BidNetDirect row text format:
          RFP-MM-06202025 RFP - Training and Technical Assistance ... Texas Calendar Published 07/09/2025 Clock Closed Bid 07/25/2025
        """
        raw_text = row.get_text(separator=" ", strip=True)
        if len(raw_text) < 20:
            return None

        # Skip header / summary rows (no solicitation number at start)
        first_token = raw_text.split()[0] if raw_text.split() else ""
        is_sol_row  = SOL_NUM_RE.match(first_token)

        # Also accept rows where a child link has a solicitation-looking href
        link = row.find("a", href=re.compile(r"/solicitation|/bid|/rfp", re.I))

        if not is_sol_row and not link:
            return None

        # Clean text for keyword matching (strip date/noise tokens)
        clean_text = BIDNET_NOISE.sub(" ", raw_text).strip()
        hits = self.matches(clean_text)
        if not hits:
            return None

        # Extract title — text after solicitation number up to "Texas" or "Calendar"
        title = clean_text
        if is_sol_row:
            # Drop the sol number token and take the rest up to noise markers
            parts = clean_text.split(None, 1)
            title = parts[1].split("Texas")[0].strip() if len(parts) > 1 else clean_text

        href = link["href"] if link else ""
        url  = (
            href if href.startswith("http")
            else urljoin("https://www.bidnetdirect.com", href)
        ) if href else source_url

        # Extract dates
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", raw_text)
        award_date = dates[-1] if dates else ""   # last date = close/award date

        return {
            "source":           self.source_name,
            "title":            title[:300],
            "description":      raw_text[:2000],
            "vendor":           "",
            "amount":           0.0,
            "award_date":       award_date,
            "agency":           "Bexar County",
            "url":              url,
            "matched_keywords": hits,
            "raw":              {"sol_num": first_token, "raw_text": raw_text[:500]},
        }

    def _scrape_bidnet(self, url: str, label: str) -> list[dict]:
        logger.info(f"[bexar] BidNetDirect {label}...")
        resp = self.fetch(url)
        if not resp:
            return []

        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        for row in soup.find_all("tr"):
            record = self._parse_bidnet_row(row, url)
            if record:
                results.append(record)

        return results

    # ------------------------------------------------------------------
    # CivicEngage (bexar.org)  — confirmed classes: .bidsTbl, .bidItems
    # ------------------------------------------------------------------

    def _scrape_civicengage(self) -> list[dict]:
        logger.info("[bexar] CivicEngage (bexar.org)...")
        resp = self.fetch(CIVICENGAGE)
        if not resp:
            logger.warning("[bexar] CivicEngage blocked — skipping")
            return []

        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        # .bidsTbl is the table wrapper; .bidItems are individual bid rows
        containers = soup.select(".bidsTbl tr, .bidItems, .bidItems li")
        if not containers:
            # Broader fallback
            containers = soup.select("table.cpGrid tr")

        for item in containers:
            text = item.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue
            hits = self.matches(text)
            if not hits:
                continue

            link  = item.find("a", href=True)
            title = link.get_text(strip=True) if link else text[:120]
            href  = link["href"] if link else ""
            url   = urljoin("https://www.bexar.org", href) if href else CIVICENGAGE

            results.append({
                "source":           self.source_name,
                "title":            title[:300],
                "description":      text[:2000],
                "vendor":           "",
                "amount":           0.0,
                "award_date":       "",
                "agency":           "Bexar County",
                "url":              url,
                "matched_keywords": hits,
                "raw":              {"text": text[:500]},
            })

        logger.info(f"[bexar] CivicEngage → {len(results)} hits")
        return results

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        results = []
        results.extend(self._scrape_bidnet(BIDNET_CLOSED, "closed bids"))
        results.extend(self._scrape_bidnet(BIDNET_OPEN,   "open bids"))
        results.extend(self._scrape_civicengage())

        # Deduplicate by URL
        seen, unique = set(), []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)

        logger.info(f"[bexar] → {len(unique)} total matching bids")
        return unique