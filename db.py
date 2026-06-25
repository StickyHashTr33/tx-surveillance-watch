"""
SQLite persistence layer.
Single table: awards — stores every surveillance contract found.
Deduplication via content-hash fingerprint.
"""
import sqlite3
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    return db


def init_db(db: sqlite3.Connection):
    """Create tables and indexes if they don't exist."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS awards (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint     TEXT    UNIQUE NOT NULL,
            source          TEXT    NOT NULL,
            title           TEXT    NOT NULL,
            description     TEXT,
            vendor          TEXT,
            amount          REAL,
            award_date      TEXT,
            agency          TEXT,
            url             TEXT,
            matched_keywords TEXT,
            raw_json        TEXT,
            discovered_at   TEXT    NOT NULL,
            alerted_discord INTEGER DEFAULT 0,
            alerted_rss     INTEGER DEFAULT 0,
            alerted_bluesky INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_fingerprint    ON awards(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_source         ON awards(source);
        CREATE INDEX IF NOT EXISTS idx_award_date     ON awards(award_date);
        CREATE INDEX IF NOT EXISTS idx_discovered_at  ON awards(discovered_at);

        CREATE TABLE IF NOT EXISTS scrape_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            status      TEXT,
            new_awards  INTEGER DEFAULT 0,
            error_msg   TEXT
        );
    """)
    db.commit()
    logger.debug("DB initialized")


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def make_fingerprint(source: str, title: str, vendor: str = "", amount: float = 0.0) -> str:
    """
    Stable 16-char hex fingerprint for dedup.
    Intentionally coarse: same title + vendor from same source = duplicate,
    even if dollar amount was revised slightly.
    """
    raw = f"{source}|{(title or '').lower().strip()}|{(vendor or '').lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def insert_award(db: sqlite3.Connection, record: dict) -> bool:
    """
    Insert a new award record.
    Returns True if inserted (new), False if fingerprint already exists (duplicate).
    """
    fp = make_fingerprint(
        record.get("source", ""),
        record.get("title", ""),
        record.get("vendor", ""),
        record.get("amount", 0.0) or 0.0,
    )

    try:
        db.execute(
            """
            INSERT INTO awards (
                fingerprint, source, title, description, vendor, amount,
                award_date, agency, url, matched_keywords, raw_json, discovered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fp,
                record.get("source", ""),
                (record.get("title") or "")[:500],
                (record.get("description") or "")[:2000],
                (record.get("vendor") or "")[:200],
                record.get("amount", 0.0) or 0.0,
                record.get("award_date", ""),
                (record.get("agency") or "")[:200],
                (record.get("url") or "")[:500],
                json.dumps(record.get("matched_keywords", [])),
                json.dumps(record.get("raw", {})),
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # already exists


def log_run(db: sqlite3.Connection, source: str, started_at: str,
            status: str, new_awards: int, error_msg: str = "") -> int:
    cur = db.execute(
        """
        INSERT INTO scrape_runs (source, started_at, finished_at, status, new_awards, error_msg)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source, started_at, datetime.utcnow().isoformat(), status, new_awards, error_msg),
    )
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_unalerted(db: sqlite3.Connection, channel: str, limit: int = 20) -> list[dict]:
    """Return awards not yet sent to `channel` (discord / rss / bluesky)."""
    col = f"alerted_{channel}"
    rows = db.execute(
        f"SELECT * FROM awards WHERE {col} = 0 ORDER BY discovered_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_alerted(db: sqlite3.Connection, award_id: int, channel: str):
    col = f"alerted_{channel}"
    db.execute(f"UPDATE awards SET {col} = 1 WHERE id = ?", (award_id,))
    db.commit()


def get_recent(db: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM awards ORDER BY discovered_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def stats(db: sqlite3.Connection) -> dict:
    total = db.execute("SELECT COUNT(*) FROM awards").fetchone()[0]
    by_source = {
        row["source"]: row["cnt"]
        for row in db.execute(
            "SELECT source, COUNT(*) as cnt FROM awards GROUP BY source"
        ).fetchall()
    }
    last_run = db.execute(
        "SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "total_awards": total,
        "by_source": by_source,
        "last_run": dict(last_run) if last_run else None,
    }
