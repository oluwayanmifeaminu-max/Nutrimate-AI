"""Materialize nutrimate.db from the .sql files in this folder.

Uses only the Python standard library (sqlite3) — no dependencies to install.

Usage:
    python build_db.py
"""

import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "nutrimate.db"

# Order matters: schema first, then fixed lookups, then the researched food data.
SQL_FILES = ["schema.sql", "seed_lookups.sql", "seed_foods.sql"]


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        for filename in SQL_FILES:
            path = DB_DIR / filename
            if not path.exists():
                print(f"skipping {filename} (not found yet)")
                continue
            sql = path.read_text(encoding="utf-8")
            conn.executescript(sql)
            print(f"applied {filename}")
        conn.commit()
    finally:
        conn.close()

    print(f"\nBuilt {DB_PATH}")


if __name__ == "__main__":
    main()
