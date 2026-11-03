"""SQLite storage for programs that users save and share from the playground.

Table: snippets(id, title, code, created_at)
Each saved program gets a short random id that forms its share link, e.g.
    http://localhost:5000/?s=Xy3_ab9Q
"""

import secrets
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    code       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class SnippetStore:
    def __init__(self, path):
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        # A new connection per call keeps this safe across Flask's request threads.
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, title, code):
        snippet_id = secrets.token_urlsafe(6)          # 8 URL-safe characters
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO snippets (id, title, code, created_at) VALUES (?, ?, ?, ?)",
                (snippet_id, title, code, created),     # parameterised: no SQL injection
            )
        return {"id": snippet_id, "title": title, "created_at": created}

    def get(self, snippet_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, code, created_at FROM snippets WHERE id = ?",
                (snippet_id,),
            ).fetchone()
        return dict(row) if row else None

    def recent(self, limit=10):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at FROM snippets "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
