"""SQLite connection helper.

No ORM on purpose — the schema is small and stable, and the queries in
queries.py read more clearly as plain SQL than as ORM-mapped classes.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "nutrimate.db"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} does not exist yet. Run `python db/build_db.py` from the "
            "Backend folder first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
