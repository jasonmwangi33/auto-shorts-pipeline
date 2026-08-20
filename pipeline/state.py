import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from .models import JobState

DB_PATH = Path("data") / "state.db"

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            source_hash TEXT,
            config_version TEXT,
            created_at TEXT,
            updated_at TEXT,
            extra_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def update_job_state(job_id: str, state: JobState, extra: Optional[Dict[str, Any]] = None):
    conn = get_db()
    now = datetime.utcnow().isoformat()
    extra_json = json.dumps(extra) if extra else "{}"
    conn.execute("""
        INSERT INTO jobs (job_id, state, created_at, updated_at, extra_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            state = excluded.state,
            updated_at = excluded.updated_at,
            extra_json = excluded.extra_json
    """, (job_id, state.value, now, now, extra_json))
    conn.commit()
    conn.close()
