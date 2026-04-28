#!/usr/bin/env python3
"""
Decision Engine CLI — dual-index (graph + FTS5) over ADR markdown files.

Commands:
    index           Rebuild both graph.db and search.db from decisions/*.md
    search <query>  Full-text search via FTS5, returns ranked JSON
    graph <id>      Graph traversal, returns all connected decisions as JSON
    related <id>    Combined: graph neighbors + FTS5 on shared tags
    next-id         Returns next sequential ADR ID
    serve           Start API server with Canvas visualization (default port 8877)
"""

import json
import os
import re
import sqlite3
import sys
import webbrowser
import yaml
from http.server import HTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DECISIONS_DIR = PROJECT_DIR / "decisions"
GRAPH_DB_PATH = DECISIONS_DIR / "graph.db"
SEARCH_DB_PATH = DECISIONS_DIR / "search.db"

sys.path.insert(0, str(PROJECT_DIR / "lib"))
from graphdb import GraphDB
from router import Router, APIHandler

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


def cmd_serve(port=8877, open_browser=False):
    router = Router()
    adrs_cache = []

    def _load_adrs():
        if not adrs_cache:
            adrs_cache.extend(discover_adrs())
        return adrs_cache

    @router.route('/api/nodes')
    def nodes(params):
        adrs = _load_adrs()
        results = []
        for adr in adrs:
            tags = adr.get("tags", []) or []
            results.append({
                "id": adr["id"],
                "title": adr.get("title", ""),
                "status": adr.get("status", "proposed"),
                "date": str(adr.get("date", "")),
                "tags": tags,
                "project": adr.get("project", ""),
                "file": adr.get("file", ""),
            })
        tag_filter = params.get("tag", [None])[0]
        if tag_filter:
            results = [n for n in results if tag_filter in n["tags"]]
        status_filter = params.get("status", [None])[0]
        if status_filter:
            results = [n for n in results if n["status"] == status_filter]
        project_filter = params.get("project", [None])[0]
        if project_filter:
            results = [n for n in results if n["project"].startswith(project_filter)]
        limit = int(params.get("limit", [0])[0] or 0)
        offset = int(params.get("offset", [0])[0] or 0)
        if limit:
            results = results[offset:offset + limit]
        elif offset:
            results = results[offset:]
        return {"nodes": results, "total": len(_load_adrs())}

    @router.route('/api/links')
    def links(params):
        if not GRAPH_DB_PATH.exists():
            return {"links": [], "total": 0}
        db = GraphDB(str(GRAPH_DB_PATH))
        all_links = []
        for src, rel, dst in db.list_relations():
            if rel == "superseded_by" or (rel == "related_to" and src > dst):
                continue
            all_links.append({"source": src, "target": dst, "relation": rel})
        db.close()
        node_filter = params.get("node", [None])[0]
        if node_filter:
            all_links = [l for l in all_links if l["source"] == node_filter or l["target"] == node_filter]
        rel_filter = params.get("relation", [None])[0]
        if rel_filter:
            all_links = [l for l in all_links if l["relation"] == rel_filter]
        return {"links": all_links, "total": len(all_links)}

    @router.route('/api/search')
    def search(params):
        query = params.get("q", [""])[0]
        if not query or not SEARCH_DB_PATH.exists():
            return {"query": query, "results": [], "count": 0}
        conn = sqlite3.connect(str(SEARCH_DB_PATH))
        safe_query = sanitize_fts5_query(query)
        rows = conn.execute(
            """SELECT id, title, tags, project, file, rank,
                      snippet(decisions, 3, '<b>', '</b>', '...', 32)
               FROM decisions
               WHERE decisions MATCH ?
               ORDER BY rank
               LIMIT 20""",
            (safe_query,),
        ).fetchall()
        conn.close()
        results = [
            {"id": r[0], "title": r[1], "rank": r[5], "snippet": r[6]}
            for r in rows
        ]
        return {"query": query, "results": results, "count": len(results)}

    @router.route('/api/tags')
    def tags(params):
        adrs = _load_adrs()
        tag_counts = {}
        for adr in adrs:
            for t in (adr.get("tags", []) or []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
        tag_list = sorted([{"name": k, "count": v} for k, v in tag_counts.items()], key=lambda x: -x["count"])
        return {"tags": tag_list}

    @router.route('/api/stats')
    def stats(params):
        adrs = _load_adrs()
        statuses = {}
        tag_set = set()
        for adr in adrs:
            s = adr.get("status", "proposed")
            statuses[s] = statuses.get(s, 0) + 1
            for t in (adr.get("tags", []) or []):
                tag_set.add(t)
        link_count = 0
        if GRAPH_DB_PATH.exists():
            db = GraphDB(str(GRAPH_DB_PATH))
            for src, rel, dst in db.list_relations():
                if rel == "superseded_by" or (rel == "related_to" and src > dst):
                    continue
                link_count += 1
            db.close()
        return {"nodes": len(adrs), "links": link_count, "tags": len(tag_set), "statuses": statuses}

    APIHandler.router = router
    APIHandler.static_dir = SCRIPT_DIR / 'static'

    server = HTTPServer(('localhost', port), APIHandler)
    count = len(_load_adrs())
    print(json.dumps({"serving": f"http://localhost:{port}", "nodes": count}))

    if open_browser:
        webbrowser.open(f"http://localhost:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


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
    elif cmd == "serve":
        port = 8877
        open_browser = False
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--open":
                open_browser = True
                i += 1
            else:
                i += 1
        cmd_serve(port=port, open_browser=open_browser)
    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
