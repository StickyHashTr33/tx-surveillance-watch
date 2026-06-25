"""
Texas Electronic State Business Daily (ESBD) scraper.
URLs:
  Solicitations: https://www.txsmartbuy.gov/esbd
  Awards:        https://www.txsmartbuy.gov/esbdawards

This site is a JS-rendered Angular SPA. Requires Playwright.

Install deps:
    pip install playwright
    playwright install chromium

The site's robots.txt restricts some crawlers. This tool only
accesses the public search interface for public-interest research.

NOTE: If you'd prefer zero Playwright complexity, the site
publicbidtracker.com/texas/ already aggregates ESBD data and
could be scraped with simple requests instead (see _fallback_bidtracker).
"""
import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)

AWARDS_URL       = "https://www.txsmartbuy.gov/esbdawards"
SOLICITATIONS_URL= "https://www.txsmartbuy.gov/esbd"
BIDTRACKER_URL   = "https://publicbidtracker.com/texas/"

SEARCH_TERMS = [
    "license plate recognition",
    "Flock Safety",
    "ShotSpotter",
    "facial recognition",
    "surveillance camera",
    "body camera",
    "drone",
    "Fusus",
    "Palantir",
    "Verkada",
    "Axon",
    "gunshot detection",
    "biometric",
    "unmanned aerial",
    "social media monitor",
]


class ESBDScraper(BaseScraper):
    source_name = "esbd"

    # ------------------------------------------------------------------
    # Primary: Playwright approach (full JS rendering)
    # ------------------------------------------------------------------

    def _playwright_search(self, keyword: str, base_url: str) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            logger.error(
                "[esbd] Playwright not installed.\n"
                "  pip install playwright && playwright install chromium"
            )
            return []

        results = []
        search_url = f"{base_url}?keyword={keyword.replace(' ', '+')}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(user_agent=self.session.headers["User-Agent"])
            try:
                page.goto(search_url, wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(3_000)  # let Angular render

                # Try Angular row selectors first
                rows = page.query_selector_all(
                    "tr.ng-star-inserted, .esbd-row, [class*='solicitation-row']"
                )

                if rows:
                    for row in rows:
                        text = row.inner_text()
                        hits = self.matches(text)
                        if not hits:
                            continue
                        link = row.query_selector("a")
                        href = link.get_attribute("href") if link else ""
                        url  = (
                            f"https://www.txsmartbuy.gov{href}"
                            if href and href.startswith("/")
                            else (href or base_url)
                        )
                        results.append(self._make_record(text, url, hits))
                else:
                    # Fallback: parse full rendered HTML
                    html = page.content()
                    results.extend(self._parse_rendered_html(html, base_url))

            except PWTimeout:
                logger.warning(f"[esbd] Timeout on keyword='{keyword}'")
            except Exception as e:
                logger.error(f"[esbd] Playwright error '{keyword}': {e}")
            finally:
                browser.close()

        return results

    def _parse_rendered_html(self, html: str, base_url: str) -> list[dict]:
        soup    = BeautifulSoup(html, "html.parser")
        results = []

        for link in soup.find_all("a", href=lambda h: h and "/esbd" in h):
            title     = link.get_text(strip=True)
            parent    = link.parent
            full_text = parent.get_text(separator=" ", strip=True) if parent else title
            hits      = self.matches(title, full_text)
            if not hits:
                continue

            href = link["href"]
            url  = (
                f"https://www.txsmartbuy.gov{href}"
                if href.startswith("/")
                else href
            )
            results.append(self._make_record(full_text, url, hits, title=title))

        return results

    # ------------------------------------------------------------------
    # Fallback: publicbidtracker.com (already aggregates ESBD)
    # No robots.txt restrictions; simpler than Playwright.
    # Use this if Playwright is unavailable.
    # ------------------------------------------------------------------

    def _fallback_bidtracker(self) -> list[dict]:
        """
        publicbidtracker.com/texas/open-bids/ aggregates ESBD data.
        Simpler to parse; use as fallback when Playwright isn't installed.
        """
        logger.info("[esbd-fallback] Trying publicbidtracker.com...")
        resp = self.fetch(f"{BIDTRACKER_URL}open-bids/")
        if not resp:
            return []

        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Their table has rows with bid title, agency, close date
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            texts = [c.get_text(strip=True) for c in cells]
            full  = " ".join(texts)
            hits  = self.matches(full)
            if not hits:
                continue

            link  = row.find("a", href=True)
            url   = link["href"] if link else BIDTRACKER_URL
            title = cells[0].get_text(strip=True)
            agency= cells[1].get_text(strip=True) if len(cells) > 1 else "Texas (state)"

            results.append({
                "source":           self.source_name,
                "title":            title,
                "description":      full,
                "vendor":           "",
                "amount":           0.0,
                "award_date":       "",
                "agency":           agency,
                "url":              url,
                "matched_keywords": hits,
                "raw":              {"cells": texts},
            })

        logger.info(f"[esbd-fallback] → {len(results)} results")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_record(self, text: str, url: str, hits: list,
                     title: str = "") -> dict:
        return {
            "source":           self.source_name,
            "title":            (title or text[:150]).strip(),
            "description":      text[:2000],
            "vendor":           "",
            "amount":           0.0,
            "award_date":       "",
            "agency":           "Texas (state agency)",
            "url":              url,
            "matched_keywords": hits,
            "raw":              {"text": text[:500]},
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        # Try Playwright first
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            playwright_available = True
        except ImportError:
            playwright_available = False

        if not playwright_available:
            logger.warning("[esbd] Playwright unavailable — using fallback")
            return self._fallback_bidtracker()

        all_results: list[dict] = []
        seen: set[str] = set()

        for term in SEARCH_TERMS:
            logger.info(f"[esbd] Playwright search awards: '{term}'")
            hits = self._playwright_search(term, AWARDS_URL)
            for h in hits:
                if h["url"] not in seen:
                    seen.add(h["url"])
                    all_results.append(h)

        logger.info(f"[esbd] → {len(all_results)} results")
        return all_results
