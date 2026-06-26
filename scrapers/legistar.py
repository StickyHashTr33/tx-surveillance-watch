"""
Legistar city council agenda watcher.
Covers: City of Austin (austintexas.legistar.com)

San Antonio migrated away from Legistar in 2021 — API is stale, excluded.

Speed design: title-only scan. We check EventItemTitle for each agenda item
and only make a follow-up matter detail call if the title already matched a
keyword. This keeps the run under 60 seconds instead of 40+ minutes.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL       = "https://webapi.legistar.com/v1"
REQUEST_DELAY  = 0.3   # seconds between calls — Legistar is a light read-only API
LOOKBACK_DAYS  = 45
LOOKAHEAD_DAYS = 30

LEGISTAR_CITIES = {
    "austin": {
        "client": "austintexas",
        "name":   "City of Austin",
        "web":    "austintexas.legistar.com",
    },
}


class LegistarScraper(BaseScraper):
    source_name = "legistar_agenda"

    def _get(self, client: str, path: str, params: dict = None) -> list | dict | None:
        time.sleep(REQUEST_DELAY)
        url  = f"{BASE_URL}/{client}/{path}"
        resp = self.fetch(url, params=params or {})
        if not resp:
            return None
        try:
            return resp.json()
        except Exception as e:
            logger.error(f"[legistar/{client}] JSON parse error {path}: {e}")
            return None

    def _date_filter(self) -> str:
        now   = datetime.now(timezone.utc)
        start = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        end   = (now + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%d")
        return f"EventDate ge datetime'{start}' and EventDate le datetime'{end}'"

    def _scrape_city(self, city_key: str, city: dict) -> list[dict]:
        client   = city["client"]
        web_base = f"https://{city['web']}"
        results  = []

        logger.info(f"[legistar] {city['name']} — fetching events...")

        events = self._get(client, "events", params={
            "$filter":  self._date_filter(),
            "$orderby": "EventDate desc",
            "$top":     100,
        })

        if not events:
            logger.warning(f"[legistar/{client}] No events in window")
            return []

        logger.info(f"[legistar/{client}] {len(events)} events — scanning titles...")

        for event in events:
            event_id   = event.get("EventId")
            event_date = (event.get("EventDate") or "")[:10]
            body_name  = event.get("EventBodyName", "")

            if not event_id:
                continue

            items = self._get(client, f"events/{event_id}/eventitems")
            if not items:
                continue

            for item in items:
                item_title  = (item.get("EventItemTitle") or "").strip()
                action_text = (item.get("EventItemActionText") or "").strip()
                item_num    = item.get("EventItemMinutesSequence", "")
                matter_id   = item.get("EventItemMatterId")

                # Title-only scan — no extra API call unless title already matches
                hits = self.matches(item_title, action_text)
                if not hits:
                    continue

                # Title matched — optionally enrich with matter body text
                if matter_id:
                    matter = self._get(client, f"matters/{matter_id}")
                    if matter:
                        extra = self.matches(matter.get("MatterText1") or "")
                        hits  = list(set(hits + extra))
                    url = f"{web_base}/MatterDetail.aspx?ID={matter_id}"
                else:
                    url = f"{web_base}/MeetingDetail.aspx?ID={event_id}"

                agency = f"{city['name']} / {body_name}" if body_name else city["name"]
                title  = item_title or f"Agenda Item {item_num} — {event_date}"
                desc   = f"Meeting: {event_date} | Body: {body_name} | Item #{item_num}"

                results.append({
                    "source":           self.source_name,
                    "title":            title[:300],
                    "description":      desc,
                    "vendor":           "",
                    "amount":           0.0,
                    "award_date":       event_date,
                    "agency":           agency,
                    "url":              url,
                    "matched_keywords": hits,
                    "raw": {
                        "city":       city_key,
                        "event_id":   event_id,
                        "event_date": event_date,
                        "body":       body_name,
                        "item_num":   item_num,
                        "matter_id":  matter_id,
                    },
                })

                logger.info(f"[legistar/{client}] HIT: {title[:70]} | {event_date}")

        return results

    def scrape(self) -> list[dict]:
        all_results: list[dict] = []
        seen: set[str] = set()

        for city_key, city in LEGISTAR_CITIES.items():
            try:
                for r in self._scrape_city(city_key, city):
                    key = r["url"] + r["title"][:40]
                    if key not in seen:
                        seen.add(key)
                        all_results.append(r)
            except Exception as e:
                logger.error(f"[legistar/{city_key}] Error: {e}")

        logger.info(f"[legistar] {len(all_results)} matching agenda items")
        return all_results