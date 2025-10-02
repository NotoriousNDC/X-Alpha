from __future__ import annotations
import sqlite3
from pathlib import Path

def get_conn(db_path: str | Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_schema(conn, schema_path: str | Path):
    with open(schema_path, 'r') as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
