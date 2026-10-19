import json
import os
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS case_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  case_id TEXT, name TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT, value TEXT, raw TEXT, added_at TEXT, added_via TEXT,
  UNIQUE(type, value)
);
CREATE TABLE IF NOT EXISTS stage_results (
  artifact_id INTEGER, stage TEXT, data TEXT, ran_at TEXT,
  UNIQUE(artifact_id, stage)
);
CREATE TABLE IF NOT EXISTS links (
  a TEXT, b TEXT, score REAL, evidence TEXT, computed_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT, actor TEXT, action TEXT, detail TEXT, confirmed INTEGER
);
"""


def _db_path(case_dir):
    return os.path.join(case_dir, "case.sqlite")


def _connect(case_dir):
    os.makedirs(case_dir, exist_ok=True)
    conn = sqlite3.connect(_db_path(case_dir))
    conn.executescript(SCHEMA)
    return conn


def init_case(case_dir, case_id, name):
    conn = _connect(case_dir)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO case_meta (id, case_id, name, created_at) VALUES (1, ?, ?, ?)",
            (case_id, name, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def add_artifact(case_dir, art_type, value, raw, added_via):
    conn = _connect(case_dir)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO artifacts (type, value, raw, added_at, added_via) VALUES (?,?,?,?,?)",
            (art_type, value, raw, datetime.now(timezone.utc).isoformat(timespec="seconds"), added_via),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM artifacts WHERE type=? AND value=?", (art_type, value)).fetchone()
        return row[0]
    finally:
        conn.close()


def list_artifacts(case_dir):
    conn = _connect(case_dir)
    try:
        rows = conn.execute("SELECT id, type, value, raw, added_at, added_via FROM artifacts ORDER BY id").fetchall()
        cols = ("id", "type", "value", "raw", "added_at", "added_via")
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def save_stage_result(case_dir, artifact_id, stage, data):
    conn = _connect(case_dir)
    try:
        conn.execute(
            "INSERT INTO stage_results (artifact_id, stage, data, ran_at) VALUES (?,?,?,?) "
            "ON CONFLICT(artifact_id, stage) DO UPDATE SET data=excluded.data, ran_at=excluded.ran_at",
            (artifact_id, stage, json.dumps(data, ensure_ascii=False), datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def get_stage_result(case_dir, artifact_id, stage):
    conn = _connect(case_dir)
    try:
        row = conn.execute(
            "SELECT data FROM stage_results WHERE artifact_id=? AND stage=?", (artifact_id, stage)
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def save_links(case_dir, links):
    conn = _connect(case_dir)
    try:
        conn.execute("DELETE FROM links")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.executemany(
            "INSERT INTO links (a, b, score, evidence, computed_at) VALUES (?,?,?,?,?)",
            [(l["a"], l["b"], l["score"], json.dumps(l["evidence"], ensure_ascii=False), now) for l in links],
        )
        conn.commit()
    finally:
        conn.close()


def get_links(case_dir):
    conn = _connect(case_dir)
    try:
        rows = conn.execute("SELECT a, b, score, evidence FROM links").fetchall()
        return [{"a": r[0], "b": r[1], "score": r[2], "evidence": json.loads(r[3])} for r in rows]
    finally:
        conn.close()


def append_audit(case_dir, actor, action, detail, confirmed):
    conn = _connect(case_dir)
    try:
        conn.execute(
            "INSERT INTO audit_log (ts, actor, action, detail, confirmed) VALUES (?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), actor, action, detail, int(confirmed)),
        )
        conn.commit()
    finally:
        conn.close()


def get_audit_log(case_dir):
    conn = _connect(case_dir)
    try:
        rows = conn.execute("SELECT ts, actor, action, detail, confirmed FROM audit_log ORDER BY id").fetchall()
        cols = ("ts", "actor", "action", "detail", "confirmed")
        return [dict(zip(cols, r)) | {"confirmed": bool(r[4])} for r in rows]
    finally:
        conn.close()


def count_audit_actions(case_dir, action):
    conn = _connect(case_dir)
    try:
        row = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action=?", (action,)).fetchone()
        return row[0]
    finally:
        conn.close()
