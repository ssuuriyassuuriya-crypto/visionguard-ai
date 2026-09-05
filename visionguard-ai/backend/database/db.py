import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "visionguard.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            media_type TEXT NOT NULL,
            detection_count INTEGER NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            peak_timestamp TEXT,
            output_path TEXT,
            stats TEXT,
            source_path TEXT
        )
        """
    )
    conn.commit()
    conn.close()
