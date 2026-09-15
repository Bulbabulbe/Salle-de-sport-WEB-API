import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "gym.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(conn, table: str, id: int):
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None
