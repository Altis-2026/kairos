"""
The public accuracy scoreboard.

Every ground-truth validation run — whoever triggered it, UI button or Janus
tool — is logged here, and GET /scoreboard aggregates the full history per
benchmark: how many times it has been run, the latest and mean skill scores,
and when. Published openly and rebuilt from real runs only, it is the
anti-cherry-picked-demo: if the numbers were bad, they would be bad in public.

Storage piggybacks on the same lightweight SQLite pattern as the watch feed.
"""

import os
import sqlite3
import threading
import time

_DB = os.path.join(os.path.dirname(__file__), "kairos_scoreboard.db")
_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_id TEXT NOT NULL,
                region TEXT,
                analysis_type TEXT,
                iou REAL, precision REAL, recall REAL, f1 REAL,
                ran_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def log_run(benchmark: dict, metrics: dict):
    """Record one completed validation run. Never raises — logging must not
    be able to break the validation that produced it."""
    try:
        init_db()
        with _lock, _connect() as conn:
            conn.execute(
                "INSERT INTO validation_runs (benchmark_id, region, "
                "analysis_type, iou, precision, recall, f1, ran_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    benchmark.get("id"),
                    benchmark.get("region"),
                    benchmark.get("analysis_type"),
                    metrics.get("iou"),
                    metrics.get("precision"),
                    metrics.get("recall"),
                    metrics.get("f1"),
                    time.time(),
                ),
            )
            conn.commit()
    except Exception:
        pass


def summary() -> dict:
    """Aggregate skill per benchmark across every run ever logged."""
    init_db()
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT benchmark_id, region, analysis_type,
                   COUNT(*) AS runs,
                   AVG(iou) AS mean_iou, AVG(precision) AS mean_precision,
                   AVG(recall) AS mean_recall, AVG(f1) AS mean_f1,
                   MAX(ran_at) AS last_run_at
            FROM validation_runs
            GROUP BY benchmark_id
            ORDER BY last_run_at DESC
            """
        ).fetchall()
        latest = {}
        for r in conn.execute(
            "SELECT benchmark_id, f1 FROM validation_runs ORDER BY ran_at"
        ):
            latest[r["benchmark_id"]] = r["f1"]

    def _r(v):
        return round(float(v), 3) if v is not None else None

    entries = [
        {
            "benchmark_id": r["benchmark_id"],
            "region": r["region"],
            "analysis_type": r["analysis_type"],
            "runs": r["runs"],
            "mean_iou": _r(r["mean_iou"]),
            "mean_precision": _r(r["mean_precision"]),
            "mean_recall": _r(r["mean_recall"]),
            "mean_f1": _r(r["mean_f1"]),
            "latest_f1": _r(latest.get(r["benchmark_id"])),
            "last_run_at": r["last_run_at"],
        }
        for r in rows
    ]
    return {
        "entries": entries,
        "total_runs": sum(e["runs"] for e in entries),
        "note": (
            "Every row aggregates real, reproducible validation runs against "
            "independently mapped events — nothing here is hand-entered."
        ),
    }
