"""
USAspending.gov API scraper.

Searches federal contract awards where:
  - place of performance is Texas
  - title / description matches surveillance keywords

API docs:   https://api.usaspending.gov/
Auth:       none required
Coverage:   federal awards only — but this catches DHS, DOJ, DOD grants
            flowing to Texas cities for surveillance tech
"""
import logging
from datetime import datetime, timedelta

from .base import BaseScraper

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

FIELDS = [
    "Award ID",
    "Recipient Name",
    "Start Date",
    "End Date",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Award Type",
    "Description",
    "Place of Performance State Code",
    "Place of Performance City Name",
    "generated_internal_id",
]

# Keywords worth their own dedicated API call
PRIORITY_TERMS = [
    "Flock Safety",
    "license plate recognition",
    "ALPR",
    "ShotSpotter",
    "SoundThinking",
    "facial recognition",
    "Clearview",
    "Fusus",
    "Verkada",
    "Palantir",
    "surveillance camera",
    "body worn camera",
    "body camera",
    "unmanned aerial",
    "drone surveillance",
    "gunshot detection",
    "social media monitoring",
    "predictive policing",
    "real time crime center",
    "Avigilon",
    "Genetec",
    "cellsite simulator",
    "stingray",
]


class USASpendingScraper(BaseScraper):
    source_name = "usaspending"

    def __init__(self, lookback_days: int = 90):
        super().__init__()
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------

    def _payload(self, keyword: str, page: int = 1) -> dict:
        end_date   = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
        return {
            "filters": {
                "keywords": [keyword],
                "place_of_performance_locations": [
                    {"country": "USA", "state": "TX"}
                ],
                "time_period": [{"start_date": start_date, "end_date": end_date}],
                "award_type_codes": ["A", "B", "C", "D"],  # contracts only
            },
            "fields": FIELDS,
            "page":       page,
            "limit":      100,
            "sort":       "Start Date",
            "order":      "desc",
            "subawards":  False,
        }

    def _award_url(self, internal_id: str) -> str:
        return f"https://www.usaspending.gov/award/{internal_id}/"

    def _process_item(self, item: dict) -> dict | None:
        title  = (item.get("Description") or "").strip()
        vendor = (item.get("Recipient Name") or "").strip()
        city   = (item.get("Place of Performance City Name") or "").strip()

        hits = self.matches(title, vendor)
        if not hits:
            return None

        agency = " / ".join(
            filter(None, [item.get("Awarding Agency"), item.get("Awarding Sub Agency")])
        )
        agency_str = f"{agency} → {city}, TX" if city else f"{agency} → TX"

        raw_amount = item.get("Award Amount")
        amount = float(raw_amount) if raw_amount is not None else 0.0

        return {
            "source":           self.source_name,
            "title":            title or f"Contract {item.get('Award ID', '')}",
            "description":      title,
            "vendor":           vendor,
            "amount":           amount,
            "award_date":       item.get("Start Date", ""),
            "agency":           agency_str,
            "url":              self._award_url(item.get("generated_internal_id") or item.get("Award ID", "")),
            "matched_keywords": hits,
            "raw":              dict(item),
        }

    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        all_results: list[dict] = []
        seen_ids: set[str] = set()

        for term in PRIORITY_TERMS:
            logger.info(f"[usaspending] keyword='{term}'")
            page = 1

            while page <= 5:  # cap at 500 results per keyword
                payload  = self._payload(term, page)
                resp     = self.post(ENDPOINT, json=payload)
                if resp is None:
                    break

                data = resp.json()
                rows = data.get("results", [])
                if not rows:
                    break

                for item in rows:
                    award_id = item.get("Award ID", "")
                    if award_id in seen_ids:
                        continue
                    seen_ids.add(award_id)

                    record = self._process_item(item)
                    if record:
                        all_results.append(record)

                total_pages = data.get("page_metadata", {}).get("page_count", 1)
                if page >= total_pages:
                    break
                page += 1

        logger.info(f"[usaspending] → {len(all_results)} matching awards")
        return all_results
