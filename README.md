# Texas Surveillance Contract Watch

**Automated public alerting for surveillance tech procurement by Texas governments.**

Monitors procurement portals across Texas municipalities, counties, and state agencies for contracts involving ALPR systems, facial recognition, gunshot detection, drones, predictive policing platforms, and related surveillance technology. New findings are published via RSS feed, Discord webhook, and Bluesky.

> "The data is legally public. Nobody's aggregating it cleanly and making it queryable in real time. That's the gap."

---

## What it monitors

| Source | Portal | Coverage |
|--------|--------|----------|
| **USAspending.gov** | Federal API | Federal awards to Texas recipients |
| **City of San Antonio** | Tabulations & Awards | Municipal contracts > $50K |
| **Texas ESBD** | txsmartbuy.gov/esbd | State agency awards ($25K+) |
| **Bexar County** | bexar.org/Bids.aspx | County solicitations |

### Surveillance vendors and technologies tracked

- **ALPR / License plate**: Flock Safety, Genetec, Vigilant Solutions, Rekor, Motorola Solutions
- **Gunshot detection**: ShotSpotter, SoundThinking, Shooter Detection Systems
- **Facial recognition**: Clearview AI, Cognitec, NEC NeoFace, Corsight
- **Video / CCTV**: Verkada, Avigilon, Axis, Hanwha, Dahua, Hikvision
- **Fusion platforms**: Fusus, Palantir, Forensic Logic, Mark43
- **Drones**: Axon Air, Skydio, DJI, Percepto
- **Body cameras**: Axon Enterprise, Watchguard, Digital Ally
- **Cell-site simulators**: L3Harris (Harris Corp), KeyW
- **Social media monitoring**: Babel Street, Dataminr, Voyager Labs
- **Predictive policing**, real-time crime centers, biometric systems

See `keywords.py` to add more.

---

## Quick start

```bash
git clone https://github.com/YOUR_HANDLE/tx-surveillance-watch
cd tx-surveillance-watch
pip install -r requirements.txt
playwright install chromium   # for ESBD (JS-rendered)

cp .env.example .env
# Edit .env with your Discord webhook, Bluesky handle, etc.

python main.py              # run once
python main.py --stats      # show DB stats
python main.py --loop       # run continuously (every 12h)
python main.py --source usaspending  # run a single scraper
python main.py --no-alerts  # scrape only, no Discord/Bluesky
```

---

## Alert setup

### RSS feed
Point any RSS reader at `public/feed.xml` (or `https://YOUR_HANDLE.github.io/tx-surveillance-watch/feed.xml` after GitHub Pages deployment).

### Discord
1. Open your server → channel settings → **Integrations → Webhooks → New Webhook**
2. Copy the URL → add to `.env` as `DISCORD_WEBHOOK_URL`

### Bluesky
1. Create account at [bsky.app](https://bsky.app) — e.g. `txsurveillancewatch.bsky.social`
2. **Settings → App Passwords → Generate**
3. Add to `.env` as `BLUESKY_HANDLE` and `BLUESKY_APP_PASSWORD`

---

## Automated deployment (GitHub Actions)

The included `.github/workflows/scrape.yml` runs every 12 hours on GitHub's free tier:

1. **Fork or push this repo to GitHub**
2. Add secrets in **Settings → Secrets → Actions**:
   - `DISCORD_WEBHOOK_URL`
   - `BLUESKY_HANDLE`
   - `BLUESKY_APP_PASSWORD`
3. Enable **GitHub Pages** → Source: `public/` branch
4. That's it — the action runs, commits `feed.xml` and `watchdog.db`, and Pages serves the dashboard

---

## Project structure

```
tx-surveillance-watch/
├── main.py               # Entry point / orchestrator
├── config.py             # All settings (env vars)
├── keywords.py           # Surveillance tech keyword list
├── db.py                 # SQLite persistence + dedup
│
├── scrapers/
│   ├── base.py           # BaseScraper (HTTP helpers, keyword scanning)
│   ├── usaspending.py    # USAspending.gov REST API
│   ├── cosa.py           # City of San Antonio (ASP.NET form scraper)
│   ├── esbd.py           # Texas ESBD (Playwright / fallback)
│   └── bexar.py          # Bexar County (CivicEngage)
│
├── alerts/
│   ├── rss.py            # RSS 2.0 feed generator
│   ├── discord.py        # Discord webhook embeds
│   └── bluesky.py        # Bluesky AT Protocol poster
│
├── public/
│   ├── index.html        # Static dashboard (GitHub Pages)
│   └── feed.xml          # Generated RSS feed
│
├── .github/workflows/
│   └── scrape.yml        # GitHub Actions scheduled job
│
├── .env.example          # Environment variable template
├── requirements.txt
└── watchdog.db           # SQLite database (gitignored in production)
```

---

## Adding more portals

1. Create `scrapers/yourportal.py` inheriting from `BaseScraper`
2. Implement `scrape() -> list[dict]` returning records with keys:
   `source, title, description, vendor, amount, award_date, agency, url, matched_keywords, raw`
3. Import in `scrapers/__init__.py`
4. Add to `SCRAPERS` dict in `main.py`

### High-value next targets
- **Austin**: austintexas.gov (uses Bonfire)
- **Houston**: houstontx.gov purchasing portal
- **Dallas**: dallascityhall.com
- **SAPD/Texas DPS grants**: DOJ JAG grant database (another USAspending filter)
- **City council minutes**: SA SpeakUp platform (meeting agendas often announce contracts before they're formally awarded)

---

## Legal / ethical notes

All data scraped by this tool is legally public under:
- **Texas Public Information Act** (Gov. Code Ch. 552) — municipalities must publish procurement awards
- **Federal Funding Accountability and Transparency Act (FFATA)** — USAspending data
- **Texas Local Government Code §262** — competitive bidding requirements mandate public posting

This tool performs read-only access to public-facing search interfaces. It does not attempt to access authenticated areas, bypass security measures, or collect personal information. Rate limits are respected via the `REQUEST_DELAY_SECONDS` setting.

---

## Contributing

Pull requests welcome, especially:
- New portal scrapers (Houston, Austin, Dallas, etc.)
- Additional vendor/keyword coverage
- FOIA request automation
- OSM cross-referencing (cross-check awarded contracts against mapped camera locations)

---

## Related projects

- [DeFlock](https://deflock.me) — crowdsourced Flock Safety camera map
- [EFF Atlas of Surveillance](https://atlasofsurveillance.org) — national police tech map
- [OpenStreetMap surveillance tags](https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance)
- [ADS-B Exchange](https://adsbexchange.com) — the model: unfiltered public data
