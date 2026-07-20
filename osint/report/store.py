import json
import os
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT, input TEXT, artifacts INTEGER, targets INTEGER, links INTEGER, data TEXT
);
CREATE TABLE IF NOT EXISTS targets (
  run_id INTEGER, key TEXT, kind TEXT, value TEXT, seed_count INTEGER
);
CREATE TABLE IF NOT EXISTS links (
  run_id INTEGER, a TEXT, b TEXT, score REAL, evidence TEXT
);
"""


def _connect(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save_run(output, input_name, config):
    db_path = (config.get("report", {}) or {}).get("db_path", "data/osint.sqlite")
    corr = output.get("correlation", {}) or {}
    targets = corr.get("targets", [])
    links = corr.get("links", [])

    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO runs (created_at, input, artifacts, targets, links, data) VALUES (?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                input_name,
                len(output.get("artifacts", [])),
                len(targets),
                len(links),
                json.dumps(output, ensure_ascii=False),
            ),
        )
        run_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO targets (run_id, key, kind, value, seed_count) VALUES (?,?,?,?,?)",
            [(run_id, t["key"], t["kind"], t["value"], t["seed_count"]) for t in targets],
        )
        conn.executemany(
            "INSERT INTO links (run_id, a, b, score, evidence) VALUES (?,?,?,?,?)",
            [(run_id, l["a"], l["b"], l["score"], json.dumps(l["evidence"], ensure_ascii=False)) for l in links],
        )
        conn.commit()
        return run_id, db_path
    finally:
        conn.close()


def _open_existing(db_path):
    if not os.path.exists(db_path):
        return None
    return sqlite3.connect(db_path)


_RUN_COLS = ("id", "created_at", "input", "artifacts", "targets", "links")


def get_runs(db_path, input_name=None, limit=50):
    conn = _open_existing(db_path)
    if conn is None:
        return []
    try:
        cols = ", ".join(_RUN_COLS)
        if input_name:
            rows = conn.execute(
                f"SELECT {cols} FROM runs WHERE input=? ORDER BY id DESC LIMIT ?", (input_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT {cols} FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(_RUN_COLS, r)) for r in rows]
    finally:
        conn.close()


def get_run(db_path, run_id):
    conn = _open_existing(db_path)
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def get_previous_run(db_path, input_name, before_id=None):
    conn = _open_existing(db_path)
    if conn is None:
        return None
    try:
        if before_id:
            row = conn.execute(
                "SELECT id, data FROM runs WHERE input=? AND id<? ORDER BY id DESC LIMIT 1",
                (input_name, before_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, data FROM runs WHERE input=? ORDER BY id DESC LIMIT 1", (input_name,)
            ).fetchone()
        return (row[0], json.loads(row[1])) if row else None
    finally:
        conn.close()
