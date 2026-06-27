"""
Database migration script for Smart Tire Analyzer.

Usage:
    python scripts/migrate_db.py          # Show pending migrations
    python scripts/migrate_db.py --apply  # Apply pending migrations
    python scripts/migrate_db.py --rollback  # Rollback last migration
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATIONS_DIR.mkdir(exist_ok=True)

MIGRATIONS = [
    {
        "id": "001_initial_schema",
        "description": "Create initial tables (analysis_results, users, feedback_records)",
        "up": """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id TEXT PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                health_score REAL,
                avg_tread_mm REAL,
                remaining_life_km REAL,
                wear_pattern_label TEXT,
                wear_pattern_severity TEXT,
                risk_level TEXT,
                replace_immediately INTEGER DEFAULT 0,
                confidence REAL,
                full_report TEXT,
                latitude REAL,
                longitude REAL,
                weather_condition TEXT,
                tire_brand TEXT,
                tire_model TEXT,
                tire_size TEXT,
                image_filename TEXT,
                model_version TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                gemini_key TEXT,
                mapillary_token TEXT,
                openweather_key TEXT,
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feedback_records (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP,
                feedback_type TEXT NOT NULL,
                corrected_tread_mm REAL,
                corrected_wear_pattern TEXT,
                corrected_health_score REAL,
                confidence_override REAL,
                comment TEXT,
                original_prediction TEXT,
                corrected_prediction TEXT
            );
        """,
        "down": """
            DROP TABLE IF EXISTS feedback_records;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS analysis_results;
        """,
    },
]


def _get_db_path():
    import os
    raw = os.getenv("DATABASE_URL", "")
    if "sqlite" in raw:
        path = raw.split("///")[-1]
        return Path(path) if path else Path("backend/smart_tire.db")
    logger.warning("Non-SQLite database detected; migration only supports SQLite")
    return None


def _get_applied(db_path: Path) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS _migrations (id TEXT PRIMARY KEY, applied_at TIMESTAMP)"
    )
    cursor.execute("SELECT id FROM _migrations ORDER BY id")
    applied = [row[0] for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    return applied


def _apply_migration(db_path: Path, migration: dict) -> None:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.executescript(migration["up"])
    cursor.execute(
        "INSERT OR IGNORE INTO _migrations (id, applied_at) VALUES (?, ?)",
        (migration["id"], datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def _rollback_migration(db_path: Path, migration: dict) -> None:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.executescript(migration["down"])
    cursor.execute("DELETE FROM _migrations WHERE id = ?", (migration["id"],))
    conn.commit()
    conn.close()


def show_status(db_path: Path) -> None:
    applied = _get_applied(db_path)
    logger.info("Database: %s", db_path)
    logger.info("")
    logger.info("Migrations:")
    for m in MIGRATIONS:
        status = "APPLIED" if m["id"] in applied else "PENDING"
        logger.info("  [%s] %s - %s", status, m["id"], m["description"])
    logger.info("")


def apply_pending(db_path: Path) -> None:
    applied = _get_applied(db_path)
    for m in MIGRATIONS:
        if m["id"] not in applied:
            logger.info("Applying: %s...", m["id"])
            _apply_migration(db_path, m)
            logger.info("  Done.")
        else:
            logger.info("Skipping (already applied): %s", m["id"])


def rollback_last(db_path: Path) -> None:
    applied = _get_applied(db_path)
    if not applied:
        logger.info("No migrations to rollback.")
        return
    last_id = applied[-1]
    for m in MIGRATIONS:
        if m["id"] == last_id:
            logger.info("Rolling back: %s...", m["id"])
            _rollback_migration(db_path, m)
            logger.info("  Done.")
            return
    logger.warning("Migration %s not found in migration list.", last_id)


def main():
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument("--apply", action="store_true", help="Apply pending migrations")
    parser.add_argument("--rollback", action="store_true", help="Rollback last migration")
    args = parser.parse_args()

    db_path = _get_db_path()
    if db_path is None:
        return

    if not db_path.exists():
        logger.info("Database not found at %s. Run the backend first to create it.", db_path)
        return

    if args.apply:
        apply_pending(db_path)
    elif args.rollback:
        rollback_last(db_path)
    else:
        show_status(db_path)


if __name__ == "__main__":
    main()
