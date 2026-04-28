#!/usr/bin/env python3
"""
Decision Engine CLI — single-db (brain.db) over decision markdown files.

Commands:
    index           Rebuild brain.db from ~/.claude/decisions/*.md
    next-id         Returns next sequential integer ID
    search <query>  FTS5 full-text search (--project, --type filters)
    graph <id>      Traverse relationships, return connected records
    related <id>    Graph neighbors + tag-matched records
"""

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from frontmatter import parse as parse_frontmatter

DECISIONS_DIR = Path.home() / ".claude" / "decisions"
DB_PATH = DECISIONS_DIR / "brain.db"

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('decision', 'knowledge', 'context')),
        status TEXT NOT NULL CHECK(status IN ('active', 'superseded', 'deprecated')),
        date TEXT,
        project TEXT,
        tags_json TEXT DEFAULT '[]',
        affects_json TEXT DEFAULT '[]',
        recorded_by TEXT,
        body TEXT,
        file TEXT
    )""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
        id, title, tags, body, project,
        tokenize='porter unicode61'
    )""",
    """CREATE TABLE IF NOT EXISTS relationships (
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        relation_type TEXT NOT NULL CHECK(relation_type IN ('supersedes', 'superseded_by', 'related_to')),
        UNIQUE(source_id, target_id, relation_type)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id)",
]


def init_db() -> sqlite3.Connection:
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    for sql in SCHEMA_SQL:
        conn.execute(sql)
    conn.commit()
    return conn


def parse_record(filepath: Path) -> dict | None:
    text = filepath.read_text(encoding="utf-8")
    try:
        meta, body = parse_frontmatter(text)
    except ValueError:
        return None
    if not meta or "id" not in meta:
        return None
    meta["body"] = body
    meta["file"] = filepath.name
    return meta


def discover_records() -> list[dict]:
    records = []
    for f in sorted(DECISIONS_DIR.glob("[0-9][0-9][0-9]-*.md")):
        rec = parse_record(f)
        if rec:
            records.append(rec)
    return records


def index_records(conn: sqlite3.Connection, records: list[dict]):
    conn.execute("DELETE FROM decisions")
    conn.execute("DELETE FROM decisions_fts")
    conn.execute("DELETE FROM relationships")

    for rec in records:
        tags = rec.get("tags") or []
        affects = rec.get("affects") or []
        conn.execute(
            """INSERT INTO decisions (id, title, type, status, date, project,
               tags_json, affects_json, recorded_by, body, file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                int(rec["id"]),
                rec.get("title", ""),
                rec.get("type", "decision"),
                rec.get("status", "active"),
                str(rec.get("date", "")),
                rec.get("project", ""),
                json.dumps(tags),
                json.dumps(affects),
                rec.get("recorded_by", ""),
                rec.get("body", ""),
                rec.get("file", ""),
            ),
        )
        conn.execute(
            "INSERT INTO decisions_fts (id, title, tags, body, project) VALUES (?, ?, ?, ?, ?)",
            (
                int(rec["id"]),
                rec.get("title", ""),
                " ".join(tags),
                rec.get("body", ""),
                rec.get("project", ""),
            ),
        )

        for superseded_id in rec.get("supersedes") or []:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (int(rec["id"]), int(superseded_id), "supersedes"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (int(superseded_id), int(rec["id"]), "superseded_by"),
            )

        for related_id in rec.get("related") or []:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (int(rec["id"]), int(related_id), "related_to"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (int(related_id), int(rec["id"]), "related_to"),
            )

    conn.commit()


def cmd_index():
    conn = init_db()
    records = discover_records()
    index_records(conn, records)
    conn.close()
    print(json.dumps({"indexed": len(records), "db": str(DB_PATH)}))


def cmd_next_id():
    conn = init_db()
    row = conn.execute("SELECT MAX(id) FROM decisions").fetchone()
    conn.close()
    next_id = (row[0] or 0) + 1
    print(json.dumps({"next_id": next_id}))


def detect_project() -> str:
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        match = re.search(r"[/:]([^/:]+?)(?:\.git)?$", url)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return Path.cwd().name


def cmd_search(args: list[str]):
    project_filter = None
    type_filter = None
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] == "--project" and i + 1 < len(args):
            project_filter = args[i + 1]
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            type_filter = args[i + 1]
            i += 2
        else:
            query_parts.append(args[i])
            i += 1

    query = " ".join(query_parts)
    if not query:
        print(json.dumps({"error": "search requires a query"}))
        sys.exit(1)

    # Quote each token to prevent FTS5 operator interpretation (e.g. hyphens as NOT)
    fts_query = " ".join(f'"{token}"' for token in query.split())

    conn = init_db()
    rows = conn.execute(
        """SELECT f.id, f.title, f.tags, f.project, rank
           FROM decisions_fts f
           WHERE decisions_fts MATCH ?
           ORDER BY rank""",
        (fts_query,),
    ).fetchall()

    results = []
    for row in rows:
        rid, title, tags, project, rank = row
        if project_filter and project_filter.lower() not in (project or "").lower():
            continue
        if type_filter:
            meta = conn.execute(
                "SELECT type FROM decisions WHERE id = ?", (int(rid),)
            ).fetchone()
            if not meta or meta[0] != type_filter:
                continue
        results.append({
            "id": int(rid),
            "title": title,
            "tags": tags,
            "project": project,
            "rank": rank,
        })

    conn.close()
    print(json.dumps({"query": query, "count": len(results), "results": results}))


def cmd_graph(args: list[str]):
    if not args:
        print(json.dumps({"error": "graph requires a record ID"}))
        sys.exit(1)

    record_id = int(args[0])
    conn = init_db()

    visited = set()
    nodes = []
    edges = []

    def walk(rid: int, depth: int):
        if rid in visited or depth > 3:
            return
        visited.add(rid)
        row = conn.execute(
            "SELECT id, title, type, status, project, tags_json FROM decisions WHERE id = ?",
            (rid,),
        ).fetchone()
        if row:
            nodes.append({
                "id": row[0], "title": row[1], "type": row[2],
                "status": row[3], "project": row[4],
                "tags": json.loads(row[5] or "[]"),
            })
        rels = conn.execute(
            "SELECT target_id, relation_type FROM relationships WHERE source_id = ?",
            (rid,),
        ).fetchall()
        for target_id, rel_type in rels:
            edges.append({"source": rid, "target": target_id, "relation": rel_type})
            if target_id not in visited:
                walk(target_id, depth + 1)

    walk(record_id, 0)
    conn.close()
    print(json.dumps({"root": record_id, "nodes": nodes, "edges": edges}))


def cmd_related(args: list[str]):
    if not args:
        print(json.dumps({"error": "related requires a record ID"}))
        sys.exit(1)

    record_id = int(args[0])
    conn = init_db()

    root = conn.execute(
        "SELECT id, title, type, status, project, tags_json FROM decisions WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not root:
        conn.close()
        print(json.dumps({"error": f"record {record_id} not found"}))
        sys.exit(1)

    seen_ids = {record_id}
    results = []

    # Graph neighbors
    rels = conn.execute(
        "SELECT target_id, relation_type FROM relationships WHERE source_id = ?",
        (record_id,),
    ).fetchall()
    for target_id, rel_type in rels:
        if target_id not in seen_ids:
            seen_ids.add(target_id)
            row = conn.execute(
                "SELECT id, title, type, status, project, tags_json FROM decisions WHERE id = ?",
                (target_id,),
            ).fetchone()
            if row:
                results.append({
                    "id": row[0], "title": row[1], "type": row[2],
                    "status": row[3], "project": row[4],
                    "tags": json.loads(row[5] or "[]"),
                    "via": rel_type,
                })

    # Tag-matched records
    root_tags = json.loads(root[5] or "[]")
    if root_tags:
        all_rows = conn.execute(
            "SELECT id, title, type, status, project, tags_json FROM decisions"
        ).fetchall()
        for row in all_rows:
            if row[0] in seen_ids:
                continue
            row_tags = json.loads(row[5] or "[]")
            shared = set(root_tags) & set(row_tags)
            if shared:
                seen_ids.add(row[0])
                results.append({
                    "id": row[0], "title": row[1], "type": row[2],
                    "status": row[3], "project": row[4],
                    "tags": json.loads(row[5] or "[]"),
                    "via": f"shared_tags:{','.join(sorted(shared))}",
                })

    conn.close()
    print(json.dumps({"root": record_id, "count": len(results), "related": results}))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "index":
        cmd_index()
    elif cmd == "next-id":
        cmd_next_id()
    elif cmd == "search":
        cmd_search(rest)
    elif cmd == "graph":
        cmd_graph(rest)
    elif cmd == "related":
        cmd_related(rest)
    elif cmd == "detect-project":
        print(json.dumps({"project": detect_project()}))
    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
