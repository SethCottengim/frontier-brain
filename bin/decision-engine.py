#!/usr/bin/env python3
"""
Decision Engine CLI — dual-index (graph + FTS5) over ADR markdown files.

Commands:
    index           Rebuild both graph.db and search.db from decisions/*.md
    search <query>  Full-text search via FTS5, returns ranked JSON
    graph <id>      Graph traversal, returns all connected decisions as JSON
    related <id>    Combined: graph neighbors + FTS5 on shared tags
    next-id         Returns next sequential ADR ID
"""

import json
import os
import re
import sqlite3
import sys
import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DECISIONS_DIR = PROJECT_DIR / "decisions"
GRAPH_DB_PATH = DECISIONS_DIR / "graph.db"
SEARCH_DB_PATH = DECISIONS_DIR / "search.db"

sys.path.insert(0, str(PROJECT_DIR / "lib"))
from graphdb import GraphDB

INVERSE_RELATIONS = {
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
    "related_to": "related_to",
    "informs": "informed_by",
    "informed_by": "informs",
    "contradicts": "contradicts",
    "refines": "refined_by",
    "refined_by": "refines",
}


def parse_adr(filepath: Path) -> dict | None:
    text = filepath.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not meta or "id" not in meta:
        return None
    meta["body"] = parts[2].strip()
    meta["file"] = str(filepath.relative_to(PROJECT_DIR))
    return meta


def discover_adrs() -> list[dict]:
    adrs = []
    for f in sorted(DECISIONS_DIR.glob("ADR-*.md")):
        adr = parse_adr(f)
        if adr:
            adrs.append(adr)
    return adrs


def build_search_db(adrs: list[dict]):
    if SEARCH_DB_PATH.exists():
        SEARCH_DB_PATH.unlink()
    conn = sqlite3.connect(str(SEARCH_DB_PATH))
    conn.execute(
        """CREATE VIRTUAL TABLE IF NOT EXISTS decisions USING fts5(
            id, title, tags, body, project, file,
            tokenize='porter unicode61'
        )"""
    )
    for adr in adrs:
        tags = " ".join(adr.get("tags", []) or [])
        conn.execute(
            "INSERT INTO decisions (id, title, tags, body, project, file) VALUES (?,?,?,?,?,?)",
            (
                adr["id"],
                adr.get("title", ""),
                tags,
                adr.get("body", ""),
                adr.get("project", ""),
                adr.get("file", ""),
            ),
        )
    conn.commit()
    conn.close()


def build_graph_db(adrs: list[dict]):
    if GRAPH_DB_PATH.exists():
        GRAPH_DB_PATH.unlink()
    db = GraphDB(str(GRAPH_DB_PATH))
    for adr in adrs:
        adr_id = adr["id"]
        for superseded_id in adr.get("supersedes", None) or []:
            db.store_relation(adr_id, "supersedes", superseded_id)
            db.store_relation(superseded_id, "superseded_by", adr_id)
        for related_id in adr.get("related", None) or []:
            db.store_relation(adr_id, "related_to", related_id)
            db.store_relation(related_id, "related_to", adr_id)
    db.close()


def cmd_index():
    adrs = discover_adrs()
    build_search_db(adrs)
    build_graph_db(adrs)
    print(json.dumps({"indexed": len(adrs), "graph_db": str(GRAPH_DB_PATH), "search_db": str(SEARCH_DB_PATH)}))


def sanitize_fts5_query(query: str) -> str:
    tokens = query.split()
    sanitized = []
    for t in tokens:
        clean = re.sub(r'[^\w-]', '', t)
        if clean:
            sanitized.append('"' + clean + '"')
    return " OR ".join(sanitized) if sanitized else query


def cmd_search(query: str):
    if not SEARCH_DB_PATH.exists():
        print(json.dumps({"error": "search.db not found — run 'index' first"}))
        sys.exit(1)
    conn = sqlite3.connect(str(SEARCH_DB_PATH))
    safe_query = sanitize_fts5_query(query)
    rows = conn.execute(
        """SELECT id, title, tags, project, file, rank
           FROM decisions
           WHERE decisions MATCH ?
           ORDER BY rank
           LIMIT 20""",
        (safe_query,),
    ).fetchall()
    conn.close()
    results = [
        {"id": r[0], "title": r[1], "tags": r[2], "project": r[3], "file": r[4], "rank": r[5]}
        for r in rows
    ]
    print(json.dumps({"query": query, "count": len(results), "results": results}))


def cmd_graph(adr_id: str):
    if not GRAPH_DB_PATH.exists():
        print(json.dumps({"error": "graph.db not found — run 'index' first"}))
        sys.exit(1)
    db = GraphDB(str(GRAPH_DB_PATH))
    outgoing = {}
    for rel in db.relations_of(adr_id):
        outgoing[rel] = list(db.find(adr_id, rel))
    incoming = {}
    for src, rel in db.relations_to(adr_id):
        incoming.setdefault(rel, []).append(src)
    db.close()
    print(json.dumps({"id": adr_id, "outgoing": outgoing, "incoming": incoming}))


def cmd_related(adr_id: str):
    if not GRAPH_DB_PATH.exists() or not SEARCH_DB_PATH.exists():
        print(json.dumps({"error": "databases not found — run 'index' first"}))
        sys.exit(1)
    db = GraphDB(str(GRAPH_DB_PATH))
    neighbors = set()
    for rel in db.relations_of(adr_id):
        for dst in db.find(adr_id, rel):
            neighbors.add(dst)
    for src, rel in db.relations_to(adr_id):
        neighbors.add(src)
    db.close()

    conn = sqlite3.connect(str(SEARCH_DB_PATH))
    row = conn.execute("SELECT tags FROM decisions WHERE id=?", (adr_id,)).fetchone()
    tag_matches = []
    if row and row[0]:
        tags = row[0].split()
        for tag in tags:
            quoted_tag = '"' + tag.replace('"', '') + '"'
            hits = conn.execute(
                "SELECT id FROM decisions WHERE decisions MATCH ? AND id != ?",
                (quoted_tag, adr_id),
            ).fetchall()
            for h in hits:
                if h[0] not in neighbors:
                    tag_matches.append(h[0])
    conn.close()
    print(
        json.dumps(
            {
                "id": adr_id,
                "graph_neighbors": sorted(neighbors),
                "tag_matches": sorted(set(tag_matches)),
            }
        )
    )


def cmd_next_id():
    existing = sorted(DECISIONS_DIR.glob("ADR-*.md"))
    max_num = 0
    for f in existing:
        m = re.match(r"ADR-(\d+)", f.stem)
        if m:
            max_num = max(max_num, int(m.group(1)))
    next_num = max_num + 1
    print(json.dumps({"next_id": f"ADR-{next_num:03d}", "next_num": next_num}))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "index":
        cmd_index()
    elif cmd == "search":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "usage: search <query>"}))
            sys.exit(1)
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "graph":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "usage: graph <adr-id>"}))
            sys.exit(1)
        cmd_graph(sys.argv[2])
    elif cmd == "related":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "usage: related <adr-id>"}))
            sys.exit(1)
        cmd_related(sys.argv[2])
    elif cmd == "next-id":
        cmd_next_id()
    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
