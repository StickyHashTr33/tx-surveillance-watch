"""
Surveillance technology keyword watchlist.
Edit freely — these drive all scraper searches and result filtering.
"""

# ---------------------------------------------------------------------------
# PRIMARY: High-confidence surveillance tech vendors & product names
# ---------------------------------------------------------------------------
VENDOR_KEYWORDS = [
    # ALPR / License Plate
    "Flock Safety",
    "Motorola Solutions",
    "Genetec",
    "Vigilant Solutions",
    "Rekor",
    "Tattile",

    # Gunshot detection
    "ShotSpotter",
    "SoundThinking",
    "Shooter Detection Systems",

    # Facial recognition
    "Clearview AI",
    "Clearview",
    "Cognitec",
    "NEC NeoFace",
    "Corsight",
    "Amazon Rekognition",

    # Video surveillance / CCTV
    "Verkada",
    "Avigilon",
    "Axis Communications",
    "Hanwha",
    "Dahua",
    "Hikvision",
    "i2 Analyst Notebook",

    # Fusion / real-time crime platforms
    "Fusus",
    "Palantir",
    "Forensic Logic",
    "Mark43",
    "Tyler Technologies",

    # Drone / UAS vendors
    "Axon Air",
    "Skydio",
    "DJI",
    "Joburg",
    "Percepto",

    # Body camera / in-car
    "Axon Enterprise",
    "Watchguard",
    "Digital Ally",

    # Cell-site simulators (stingrays)
    "Harris Corporation",
    "L3Harris",
    "KeyW",

    # Social media / OSINT
    "Babel Street",
    "Dataminr",
    "Voyager Labs",
    "Skopenow",
    "Social Links",
    "Media Sonar",
]

# ---------------------------------------------------------------------------
# SECONDARY: Technology category terms (broader, more noise)
# ---------------------------------------------------------------------------
TECH_KEYWORDS = [
    # ALPR
    "license plate recognition",
    "automated license plate",
    "ALPR",
    "ANPR",

    # Surveillance
    "gunshot detection",
    "acoustic detection",
    "ShotSpotter",
    "facial recognition",
    "face recognition",
    "biometric identification",
    "video analytics",
    "video surveillance",

    # Drones
    "unmanned aerial",
    " UAS ",
    "drone surveillance",
    "drone program",

    # Cell tracking
    "cellsite simulator",
    "IMSI catcher",
    "stingray device",

    # Data platforms
    "predictive policing",
    "social media monitoring",
    "social media intelligence",

    # Infrastructure
    "real time crime center",
    "RTCC",
    "surveillance camera",
    "body worn camera",
    "body camera",
]

# ---------------------------------------------------------------------------
# Combined list used by scrapers
# ---------------------------------------------------------------------------
ALL_KEYWORDS = VENDOR_KEYWORDS + TECH_KEYWORDS


def scan(text: str) -> list[str]:
    """Return all keywords found in text (case-insensitive)."""
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in ALL_KEYWORDS if kw.lower() in text_lower]


def matches(*fields: str) -> list[str]:
    """Scan multiple text fields, return deduplicated keyword hits."""
    combined = " ".join(f for f in fields if f)
    return list(set(scan(combined)))
