"""
Janus project memory — the mentor's persistent state.

A research project is a long-lived thread: the question, the evolving study
design, every conversation turn (including what tools Janus ran and what they
returned), and the annotated bibliography. SQLite for now, same pattern as
watch/store.py; moves to Firestore/Cloud SQL before the paid launch
(docs/JANUS.md §6).

Projects are keyed by an `owner` string: the Firebase uid for signed-in
users, or an anonymous per-browser id the frontend keeps in localStorage.
"""

import json
import os
import sqlite3
import threading
import time

DB_PATH = os.getenv("JANUS_DB_PATH", "kairos_janus.db")

_lock = threading.Lock()

# Keep prompts bounded: only the most recent turns ride into the model.
HISTORY_LIMIT = 30


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                title TEXT NOT NULL,
                question TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'exploring',
                curriculum_id TEXT,
                curriculum_session INTEGER DEFAULT 0,
                design TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT,
                tool_events TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bibliography (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                venue TEXT,
                url TEXT,
                note TEXT,
                created_at REAL NOT NULL,
                UNIQUE(project_id, title)
            )
            """
        )
        conn.commit()


# --- projects ---------------------------------------------------------------


def create_project(
    owner: str,
    title: str,
    question: str = "",
    curriculum_id: str = None,
) -> dict:
    now = time.time()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (owner, title, question, curriculum_id, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (owner, title, question, curriculum_id, now, now),
        )
        conn.commit()
        project_id = int(cur.lastrowid)
    return get_project(project_id)


def get_project(project_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if not row:
        raise ValueError(f"Project {project_id} not found.")
    p = dict(row)
    p["design"] = json.loads(p["design"] or "{}")
    return p


def list_projects(owner: str) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM projects WHERE owner = ? ORDER BY updated_at DESC",
            (owner,),
        ).fetchall()
    out = []
    for row in rows:
        p = dict(row)
        p["design"] = json.loads(p["design"] or "{}")
        out.append(p)
    return out


def update_project(project_id: int, **fields) -> dict:
    """Update whitelisted columns; design dicts are merged, not replaced."""
    allowed = {"title", "question", "stage", "curriculum_id", "curriculum_session"}
    sets, values = [], []
    design_patch = fields.pop("design", None)

    for key, value in fields.items():
        if key in allowed and value is not None:
            sets.append(f"{key} = ?")
            values.append(value)

    with _lock, _connect() as conn:
        if design_patch:
            row = conn.execute(
                "SELECT design FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Project {project_id} not found.")
            merged = json.loads(row["design"] or "{}")
            merged.update({k: v for k, v in design_patch.items() if v is not None})
            sets.append("design = ?")
            values.append(json.dumps(merged))
        if sets:
            sets.append("updated_at = ?")
            values.append(time.time())
            values.append(project_id)
            conn.execute(
                f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", values
            )
            conn.commit()
    return get_project(project_id)


def delete_project(project_id: int):
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM messages WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM bibliography WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()


# --- messages ---------------------------------------------------------------


def add_message(
    project_id: int,
    role: str,
    content: str,
    mode: str = None,
    tool_events: list = None,
) -> dict:
    now = time.time()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (project_id, role, content, mode, "
            "tool_events, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                project_id,
                role,
                content,
                mode,
                json.dumps(tool_events) if tool_events else None,
                now,
            ),
        )
        conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id)
        )
        conn.commit()
        message_id = int(cur.lastrowid)
    return {
        "id": message_id,
        "project_id": project_id,
        "role": role,
        "content": content,
        "mode": mode,
        "tool_events": tool_events or [],
        "created_at": now,
    }


def get_messages(project_id: int, limit: int = 200) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE project_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    out = []
    for row in rows:
        m = dict(row)
        m["tool_events"] = json.loads(m["tool_events"]) if m["tool_events"] else []
        out.append(m)
    return out


def recent_history(project_id: int, limit: int = HISTORY_LIMIT) -> list:
    """The tail of the conversation, oldest first, for the model context."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE project_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# --- bibliography -----------------------------------------------------------


def add_reference(
    project_id: int,
    title: str,
    authors: str = None,
    year: int = None,
    venue: str = None,
    url: str = None,
    note: str = None,
) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO bibliography (project_id, title, authors, "
            "year, venue, url, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, title, authors, year, venue, url, note, time.time()),
        )
        conn.commit()
        return cur.rowcount > 0


def get_bibliography(project_id: int) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM bibliography WHERE project_id = ? "
            "ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]
