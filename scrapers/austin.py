"""
City of Austin contracts scraper.
Dataset: https://data.austintexas.gov/Budget-and-Finance/Contracts/84ih-p28j

Uses the CSV download endpoint directly — no API version issues,
no authentication required, confirmed working.

Downloads the full dataset once per run and keyword-scans in Python.
Dataset is ~2MB, fine for a twice-daily scraper.
"""
import csv
import io
import logging
from datetime import datetime

from .base import BaseScraper

logger = logging.getLogger(__name__)

CSV_URL    = "https://data.austintexas.gov/api/views/84ih-p28j/rows.csv?accessType=DOWNLOAD"
DETAIL_URL = "https://data.austintexas.gov/Budget-and-Finance/Contracts/84ih-p28j"


class AustinScraper(BaseScraper):
    source_name = "austin_contracts"

    def _parse_amount(self, row: dict) -> float:
        for field in ("MA_ITD_ORD_AM", "MA_PRCH_LMT_AM"):
            val = row.get(field, "")
            if val:
                try:
                    return float(str(val).replace(",", "").strip())
                except (ValueError, TypeError):
                    pass
        return 0.0

    def _parse_date(self, row: dict) -> str:
        for field in ("BRD_AWD_DT", "EFBGN_DT"):
            val = (row.get(field) or "").strip()
            if not val:
                continue
            for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(val[:10], fmt[:10]).strftime("%Y-%m-%d")
                except ValueError:
                    pass
        return ""

    def _make_record(self, row: dict, hits: list) -> dict:
        desc     = (row.get("DOC_DSCR")          or "").strip()
        synopsis = (row.get("CONTRACT_SYNOPSIS")  or "").strip()
        vendor   = (row.get("LGL_NM")             or "").strip()
        alias    = (row.get("ALIAS_NM")            or "").strip()
        cat      = (row.get("CAT_DSCR")           or "").strip()
        rpt      = (row.get("RPT_DSCR")           or "").strip()
        doc_id   = (row.get("DOC_ID")             or "").strip()

        title          = desc or synopsis or f"Contract {doc_id}"
        vendor_display = alias if alias and alias.upper() not in ("N/A", "") else vendor

        agency_parts = ["City of Austin"]
        if cat: agency_parts.append(cat)
        if rpt: agency_parts.append(rpt)

        return {
            "source":           self.source_name,
            "title":            title[:300],
            "description":      (synopsis or desc)[:2000],
            "vendor":           vendor_display,
            "amount":           self._parse_amount(row),
            "award_date":       self._parse_date(row),
            "agency":           " / ".join(agency_parts),
            "url":              f"{DETAIL_URL}?q={doc_id}" if doc_id else DETAIL_URL,
            "matched_keywords": hits,
            "raw":              {k: v for k, v in row.items() if v and v != "unknown"},
        }

    def scrape(self) -> list[dict]:
        logger.info("[austin] Downloading contract CSV...")
        resp = self.fetch(CSV_URL)
        if not resp:
            logger.error("[austin] Could not download CSV")
            return []

        logger.info(f"[austin] Downloaded {len(resp.content):,} bytes — scanning...")

        results = []
        seen: set[str] = set()
        total_rows = 0

        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            total_rows += 1

            desc     = row.get("DOC_DSCR", "")
            synopsis = row.get("CONTRACT_SYNOPSIS", "")
            vendor   = row.get("LGL_NM", "")
            alias    = row.get("ALIAS_NM", "")

            hits = self.matches(desc, synopsis, vendor, alias)
            if not hits:
                continue

            doc_id = row.get("DOC_ID", "")
            vendor_key = vendor + desc[:30]
            key = doc_id or vendor_key
            if key in seen:
                continue
            seen.add(key)

            results.append(self._make_record(row, hits))

        logger.info(f"[austin] Scanned {total_rows:,} rows — {len(results)} matches")
        return results