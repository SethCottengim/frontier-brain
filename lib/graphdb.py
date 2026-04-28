"""
Relationship graph for decision records.

Operates within a shared SQLite database (brain.db). Tables coexist
alongside the decisions table and FTS5 virtual table.

Only three relation types: supersedes, superseded_by, related_to.
All IDs are integers matching decision record IDs.
"""

import sqlite3

RELATION_TYPES = ("supersedes", "superseded_by", "related_to")

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS relationships (
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        relation_type TEXT NOT NULL CHECK(relation_type IN ('supersedes', 'superseded_by', 'related_to')),
        UNIQUE(source_id, target_id, relation_type)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id)",
]

AUTO_INVERSE = {
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
    "related_to": "related_to",
}


class GraphDB:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        for sql in SCHEMA_SQL:
            self._conn.execute(sql)
        self._conn.commit()

    def store(self, source_id: int, relation: str, target_id: int):
        if relation not in RELATION_TYPES:
            raise ValueError(f"Unknown relation: {relation}. Must be one of {RELATION_TYPES}")
        self._conn.execute(
            "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (source_id, target_id, relation),
        )
        inverse = AUTO_INVERSE[relation]
        self._conn.execute(
            "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (target_id, source_id, inverse),
        )
        self._conn.commit()

    def neighbors(self, record_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT target_id, relation_type FROM relationships WHERE source_id = ?",
            (record_id,),
        ).fetchall()
        return [{"id": r[0], "relation": r[1]} for r in rows]

    def traverse(self, record_id: int, max_depth: int = 3) -> dict:
        visited = set()
        nodes = []
        edges = []

        def _walk(rid: int, depth: int):
            if rid in visited or depth > max_depth:
                return
            visited.add(rid)
            for neighbor in self.neighbors(rid):
                tid = neighbor["id"]
                edges.append({"source": rid, "target": tid, "relation": neighbor["relation"]})
                if tid not in visited:
                    _walk(tid, depth + 1)

        _walk(record_id, 0)
        nodes = list(visited)
        return {"nodes": nodes, "edges": edges}

    def all_edges(self) -> list[tuple[int, int, str]]:
        rows = self._conn.execute(
            "SELECT source_id, target_id, relation_type FROM relationships"
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    def delete_for(self, record_id: int):
        self._conn.execute("DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (record_id, record_id))
        self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM relationships")
        self._conn.commit()
