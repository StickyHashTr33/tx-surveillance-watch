"""
City of San Antonio — Tabulations & Awards scraper.
URL: https://webapp1.sanantonio.gov/TabulationsAwards/

This is an ASP.NET WebForms page. Workflow:
  1. GET the page → extract __VIEWSTATE / __EVENTVALIDATION
  2. POST back with search keywords → parse results table
  3. For each hit, extract solicitation metadata

Coverage: contracts > $50K facilitated by COSA Procurement Division.
Note: page says it does NOT include all council-approved contracts.
     Full coverage requires also parsing COSA City Council A-session agendas.
"""
import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://webapp1.sanantonio.gov/TabulationsAwards/"

# Description terms to search (short phrases that fit the form's search box well)
SEARCH_TERMS = [
    "surveillance",
    "camera",
    "license plate",
    "Flock",
    "ShotSpotter",
    "facial",
    "drone",
    "body camera",
    "Axon",
    "Fusus",
    "Palantir",
    "biometric",
    "gunshot",
    "acoustic",
    "predictive",
    "social media monitor",
    "unmanned",
]


class COSAScraper(BaseScraper):
    source_name = "cosa_awards"

    # ------------------------------------------------------------------
    # Step 1: get ViewState
    # ------------------------------------------------------------------

    def _get_aspnet_fields(self) -> dict:
        """
        Fetch the search page and extract the hidden ASP.NET fields
        required to POST a search form.
        """
        resp = self.fetch(BASE_URL)
        if not resp:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")

        fields = {}
        for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
            tag = soup.find("input", {"name": name})
            if tag:
                fields[name] = tag.get("value", "")
            else:
                fields[name] = ""

        # Also capture any other hidden fields (some ASP.NET apps need them)
        for tag in soup.find_all("input", type="hidden"):
            n = tag.get("name", "")
            if n and n not in fields:
                fields[n] = tag.get("value", "")

        logger.debug(f"[cosa] ViewState keys: {list(fields.keys())}")
        return fields

    # ------------------------------------------------------------------
    # Step 2: POST search
    # ------------------------------------------------------------------

    def _search(self, description_term: str, aspnet_fields: dict) -> list[dict]:
        """
        POST a keyword search to the COSA awards page.
        Returns a list of raw result dicts.
        """
        # Discover the search button's name dynamically — avoids hardcoding
        # control IDs that may change. Fall back to common patterns.
        payload = {
            **aspnet_fields,
            # These control IDs follow the standard COSA WebForms naming.
            # If the site is restructured, update these via browser DevTools.
            "ctl00$ContentPlaceHolder1$ddlContractType": "0",    # All types
            "ctl00$ContentPlaceHolder1$txtDescription":  description_term,
            "ctl00$ContentPlaceHolder1$btnSearch":       "Search",
        }

        resp = self.post(BASE_URL, data=payload)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # The results table usually has id containing "GridView" or "gvResults"
        table = (
            soup.find("table", id=re.compile(r"GridView|gvResult|tblResult", re.I))
            or soup.find("table", class_=re.compile(r"grid|results", re.I))
        )

        if not table:
            # Last resort: any data table with 4+ columns
            for tbl in soup.find_all("table"):
                rows = tbl.find_all("tr")
                if len(rows) > 1 and len(rows[1].find_all("td")) >= 4:
                    table = tbl
                    break

        if not table:
            logger.debug(f"[cosa] No results table found for '{description_term}'")
            return []

        records = []
        header_row = table.find("tr")
        data_rows  = table.find_all("tr")[1:]  # skip header

        for row in data_rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            col_texts = [c.get_text(strip=True) for c in cols]
            full_text = " ".join(col_texts)

            hits = self.matches(*col_texts)
            if not hits:
                continue

            # Try to find the record detail URL
            link_tag = row.find("a", href=True)
            url = BASE_URL
            if link_tag:
                href = link_tag["href"]
                if href.startswith("http"):
                    url = href
                elif href.startswith("/") and not href.startswith("javascript"):
                    url = f"https://webapp1.sanantonio.gov{href}"
                # javascript: postback hrefs are useless — fall back to BASE_URL

            # Parse amount from any column that looks like a dollar figure
            amount = 0.0
            for txt in col_texts:
                clean = txt.replace(",", "").replace("$", "").strip()
                if re.match(r"^\d+\.\d{2}$", clean):
                    try:
                        amount = float(clean)
                        break
                    except ValueError:
                        pass

            # Heuristic column mapping (COSA award table structure circa 2024):
            # 0: Solicitation/Bid #
            # 1: Description
            # 2: Vendor / Awardee
            # 3: Award Amount
            # 4: Award Date  (may vary)
            sol_num     = col_texts[0] if len(col_texts) > 0 else ""
            description = col_texts[1] if len(col_texts) > 1 else full_text
            vendor      = col_texts[2] if len(col_texts) > 2 else ""

            records.append({
                "source":           self.source_name,
                "title":            description or sol_num,
                "description":      description,
                "vendor":           vendor,
                "amount":           amount,
                "award_date":       col_texts[4] if len(col_texts) > 4 else "",
                "agency":           "City of San Antonio",
                "url":              url,
                "matched_keywords": hits,
                "raw":              {"sol_num": sol_num, "cols": col_texts},
            })

        return records

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        logger.info("[cosa] Fetching ASP.NET ViewState...")
        aspnet_fields = self._get_aspnet_fields()
        if not aspnet_fields:
            logger.error("[cosa] Could not load search page — skipping")
            return []

        all_results: list[dict] = []
        seen: set[str] = set()

        for term in SEARCH_TERMS:
            logger.info(f"[cosa] Searching: '{term}'")
            hits = self._search(term, aspnet_fields)
            for h in hits:
                # Dedup within this run by (title, vendor) pair
                key = f"{h['title'][:60]}|{h['vendor'][:30]}"
                if key not in seen:
                    seen.add(key)
                    all_results.append(h)

        logger.info(f"[cosa] → {len(all_results)} matching contracts")
        return all_results