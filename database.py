"""
database.py
-----------
"""

import sqlite3
import aiosqlite
from pathlib import Path

DB_PATH = Path("eventlog.db")

# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT    NOT NULL
                            CHECK(length(user_id) BETWEEN 1 AND 64),
    occurred_at_utc TEXT    NOT NULL,
    occurred_at_raw TEXT    NOT NULL,
    recorded_at     TEXT    NOT NULL,
    kind            TEXT    NOT NULL
                            CHECK(kind IN ('click','view','purchase','signup','custom')),
    tags            TEXT    NOT NULL DEFAULT '[]',
    payload         TEXT,
    UNIQUE(user_id, occurred_at_utc)
);

CREATE INDEX IF NOT EXISTS idx_events_occurred
    ON events(occurred_at_utc DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""

# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

async def get_db() -> aiosqlite.Connection:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # S'assurer que WAL et FK sont actifs sur cette connexion
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()