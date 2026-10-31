# Texas Surveillance Contract Watch

Automated public alerting for surveillance tech procurement by Texas governments.

Monitors procurement portals across Texas municipalities, counties, and state agencies for contracts involving ALPR systems, facial recognition, gunshot detection, drones, predictive policing platforms, and related surveillance technology. New findings are published via RSS feed, Discord webhook, and Bluesky.

Live dashboard: **[stickyhashtr33.github.io/tx-surveillance-watch](https://stickyhashtr33.github.io/tx-surveillance-watch)**

---

## What it monitors

| Source | Portal | Coverage |
|--------|--------|----------|
| **USAspending.gov** | Federal API | Federal awards to Texas recipients |
| **City of San Antonio** | Tabulations & Awards | Municipal contracts over $50K |
| **Texas ESBD** | txsmartbuy.gov/esbdawards | State agency awards |
| **Bexar County** | BidNetDirect | County solicitations |
| **City of Austin** | Open Data portal | Austin contracts dataset |
| **Austin City Council** | Legistar API | Agenda items 30 days out |
| **USAspending (grants)** | Federal API | DOJ/DHS grants to Texas agencies |

### Surveillance vendors and technologies tracked

- **ALPR / License plate**: Flock Safety, Genetec, Vigilant Solutions, Rekor, Motorola Solutions
- **Gunshot detection**: ShotSpotter, SoundThinking, Shooter Detection Systems
- **Facial recognition**: Clearview AI, Cognitec, NEC NeoFace, Corsight
- **Video / CCTV**: Verkada, Avigilon, Axis, Hanwha, Dahua, Hikvision
- **Fusion platforms**: Fusus, Palantir, Forensic Logic, Mark43
- **Drones**: Axon Air, Skydio, DJI, Percepto
- **Body cameras**: Axon Enterprise, Watchguard, Digital Ally
- **Cell-site simulators**: L3Harris, KeyW
- **Social media monitoring**: Babel Street, Dataminr, Voyager Labs
- **Predictive policing**, real-time crime centers, biometric systems

See `keywords.py` to add or remove terms.

---

## Quick start

```bash
git clone https://github.com/StickyHashTr33/tx-surveillance-watch
cd tx-surveillance-watch
pip install -r requirements.txt
python -m playwright install chromium   # for ESBD (JS-rendered site)

cp .env.example .env
# Edit .env with your Discord webhook, Bluesky credentials, etc.

python main.py                        # run all scrapers once
python main.py --stats                # show database stats
python main.py --loop                 # run every 12 hours
python main.py --source usaspending   # run a single scraper
python main.py --no-alerts            # scrape only, skip Discord/Bluesky
```

---

## Alert setup

**RSS feed** — point any RSS reader at `https://stickyhashtr33.github.io/tx-surveillance-watch/feed.xml`

**Discord** — Server → channel settings → Integrations → Webhooks → New Webhook → copy URL → add to `.env` as `DISCORD_WEBHOOK_URL`

**Bluesky** — create account at bsky.app → Settings → App Passwords → Generate → add handle and password to `.env`

---

## Automated deployment

Runs free on GitHub Actions twice daily (6am and 6pm UTC):

1. Push this repo to GitHub
2. Add secrets under Settings → Secrets → Actions:
   - `DISCORD_WEBHOOK_URL`
   - `BLUESKY_HANDLE`
   - `BLUESKY_APP_PASSWORD`
3. Enable GitHub Pages → Source: `docs/` folder on `main` branch
4. Trigger the first run manually under Actions → Scrape & Alert → Run workflow

The action scrapes all sources, commits the updated `feed.xml` and `watchdog.db` back to the repo, fires Discord and Bluesky alerts for new findings, and Pages serves the dashboard automatically.

---

## Project structure

```
tx-surveillance-watch/
├── main.py                   # Entry point and orchestrator
├── config.py                 # All settings via environment variables
├── keywords.py               # Surveillance tech keyword watchlist
├── db.py                     # SQLite persistence and deduplication
│
├── scrapers/
│   ├── base.py               # BaseScraper — HTTP helpers, keyword scanning
│   ├── usaspending.py        # USAspending.gov REST API
│   ├── cosa.py               # City of San Antonio ASP.NET form scraper
│   ├── esbd.py               # Texas ESBD (Playwright + publicbidtracker fallback)
│   ├── bexar.py              # Bexar County via BidNetDirect
│   ├── austin.py             # City of Austin open data CSV
│   └── legistar.py           # Austin city council agendas via Legistar API
│
├── alerts/
│   ├── rss.py                # RSS 2.0 feed generator
│   ├── discord.py            # Discord webhook embeds
│   └── bluesky.py            # Bluesky AT Protocol poster
│
├── docs/
│   ├── index.html            # Public dashboard (GitHub Pages)
│   └── feed.xml              # Generated RSS feed
│
├── .github/workflows/
│   └── scrape.yml            # GitHub Actions scheduled job
│
├── .env.example              # Environment variable template
├── requirements.txt
└── watchdog.db               # SQLite database
```

---

## Adding more portals

1. Create `scrapers/yourportal.py` inheriting from `BaseScraper`
2. Implement `scrape() -> list[dict]` returning records with keys: `source, title, description, vendor, amount, award_date, agency, url, matched_keywords, raw`
3. Import in `scrapers/__init__.py`
4. Add to `SCRAPERS` dict in `main.py`
5. Add an `ENABLE_YOURPORTAL` flag in `config.py`

### High-value next targets

- **Houston** — `data.houstontx.gov` checkbook dataset (CKAN API, vendor payment data from 2018)
- **Dallas** — `dallasopendata.com` vendor payments (Socrata)
- **San Antonio city council agendas** — SA moved off Legistar in 2021, current platform TBD
- **Texas Ethics Commission** — lobbyist registration filings for surveillance vendors
- **FAA drone waivers** — public CSV of drone authorization holders filtered by Texas public safety agencies

---

## Legal notes

All data collected by this tool is legally public under the Texas Public Information Act (Gov. Code Ch. 552), the Federal Funding Accountability and Transparency Act, and Texas Local Government Code §262. This tool performs read-only access to public-facing search interfaces. It does not access authenticated areas, bypass security controls, or collect personal information.

---

## Related projects

- [DeFlock](https://deflock.me) — crowdsourced Flock Safety camera map
- [EFF Atlas of Surveillance](https://atlasofsurveillance.org) — national police tech map
- [ADS-B Exchange](https://adsbexchange.com) — the model: unfiltered public data, no blocklist
- [OpenStreetMap surveillance tags](https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance)
- [Flock Locations](https://flocklocations.com) — public map of Flock Safety and ALPR camera locations
