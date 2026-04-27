"""
Minimal SQLite-based graph database for storing string relationships.

Inspired by CodyKochmann/graphdb but zero external dependencies.
Only stores string keys and string relation names — no dill serialization needed.
"""

import sqlite3
from threading import Lock, current_thread
from typing import Generator

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        value TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS relations (
        src INTEGER NOT NULL,
        name TEXT NOT NULL,
        dst INTEGER NOT NULL,
        UNIQUE(src, name, dst),
        FOREIGN KEY(src) REFERENCES objects(id),
        FOREIGN KEY(dst) REFERENCES objects(id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_rel_src ON relations(src)",
    "CREATE INDEX IF NOT EXISTS idx_rel_dst ON relations(dst)",
    "CREATE INDEX IF NOT EXISTS idx_rel_name ON relations(name)",
]


class GraphDB:
    def __init__(self, path=":memory:"):
        self._path = path
        self._connections: dict = {}
        self._write_lock = Lock()
        with self._write_lock:
            for sql in SCHEMA_SQL:
                self._execute(sql)
            self._conn.commit()

    @property
    def _conn(self) -> sqlite3.Connection:
        tid = current_thread().ident
        if tid not in self._connections:
            self._connections[tid] = sqlite3.connect(self._path)
        return self._connections[tid]

    def _execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def _get_id(self, value: str) -> int | None:
        row = self._execute(
            "SELECT id FROM objects WHERE value=? LIMIT 1", (value,)
        ).fetchone()
        return row[0] if row else None

    def _ensure_item(self, value: str) -> int:
        item_id = self._get_id(value)
        if item_id is not None:
            return item_id
        self._execute("INSERT OR IGNORE INTO objects (value) VALUES (?)", (value,))
        self._conn.commit()
        return self._get_id(value)

    def store_relation(self, src: str, name: str, dst: str):
        with self._write_lock:
            self._ensure_item(src)
            self._ensure_item(dst)
            self._execute(
                """INSERT OR IGNORE INTO relations (src, name, dst)
                   SELECT o1.id, ?, o2.id
                   FROM objects o1, objects o2
                   WHERE o1.value=? AND o2.value=?""",
                (name, src, dst),
            )
            self._conn.commit()

    def delete_relation(self, src: str, name: str, dst: str):
        with self._write_lock:
            src_id, dst_id = self._get_id(src), self._get_id(dst)
            if src_id is not None and dst_id is not None:
                self._execute(
                    "DELETE FROM relations WHERE src=? AND name=? AND dst=?",
                    (src_id, name, dst_id),
                )
                self._conn.commit()

    def find(self, target: str, relation: str) -> Generator[str, None, None]:
        rows = self._execute(
            """SELECT o2.value FROM relations r
               JOIN objects o1 ON r.src=o1.id
               JOIN objects o2 ON r.dst=o2.id
               WHERE o1.value=? AND r.name=?""",
            (target, relation),
        ).fetchall()
        for row in rows:
            yield row[0]

    def relations_of(self, target: str) -> Generator[str, None, None]:
        rows = self._execute(
            """SELECT DISTINCT r.name FROM relations r
               JOIN objects o ON r.src=o.id
               WHERE o.value=?""",
            (target,),
        ).fetchall()
        for row in rows:
            yield row[0]

    def relations_to(self, target: str) -> Generator[tuple[str, str], None, None]:
        rows = self._execute(
            """SELECT o_src.value, r.name FROM relations r
               JOIN objects o_dst ON r.dst=o_dst.id
               JOIN objects o_src ON r.src=o_src.id
               WHERE o_dst.value=?""",
            (target,),
        ).fetchall()
        for row in rows:
            yield row[0], row[1]

    def list_relations(self) -> Generator[tuple[str, str, str], None, None]:
        rows = self._execute(
            """SELECT o1.value, r.name, o2.value FROM relations r
               JOIN objects o1 ON r.src=o1.id
               JOIN objects o2 ON r.dst=o2.id"""
        ).fetchall()
        for row in rows:
            yield row[0], row[1], row[2]

    def list_objects(self) -> Generator[str, None, None]:
        for row in self._execute("SELECT value FROM objects").fetchall():
            yield row[0]

    def __contains__(self, target: str) -> bool:
        return self._get_id(target) is not None

    def __iter__(self):
        return self.list_objects()

    def clear(self):
        with self._write_lock:
            self._execute("DELETE FROM relations")
            self._execute("DELETE FROM objects")
            self._conn.commit()

    def close(self):
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
