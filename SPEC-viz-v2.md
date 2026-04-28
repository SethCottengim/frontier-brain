# SPEC: Scalable Visualization (viz-v2)

## Objective

Replace the inline-JSON + SVG graph visualization with a thin Python API server over existing SQLite databases and a Canvas-based renderer. Must scale to 2000+ nodes while preserving the Obsidian-style dark aesthetic, d3-force physics, and zero-external-dependency philosophy.

**Target users:** Developer (Seth) exploring decision relationships in-browser during Claude Code sessions.

**Non-goals:** Multi-user server, authentication, persistent daemon, production deployment.

## Architecture

```
decisions/*.md  →  index  →  graph.db + search.db
                                    ↓
                      decision-engine.py serve [:port]
                                    ↓
              ┌─────────────────────┼────────────────────┐
              ↓                     ↓                    ↓
    GET /api/nodes         GET /api/links       GET /api/search?q=
    (paginated, filterable) (by viewport/node)  (FTS5, highlight)
              ↓                     ↓                    ↓
              └─────────────────────┼────────────────────┘
                                    ↓
                          GET / → index.html
                          (Canvas 2D + d3-force + d3-quadtree)
```

### What stays
- `bin/visualize.py` — offline static HTML snapshot (coexists, no changes)
- `lib/graphdb/` — zero-dep SQLite graph library
- d3-force simulation — same physics, same forces, same Obsidian aesthetic
- All existing `decision-engine.py` commands (`index`, `search`, `graph`, `related`, `next-id`)

### What's new
- `serve` subcommand in `decision-engine.py`
- `lib/router.py` — minimal HTTP router (~50 lines, stdlib only)
- `bin/static/index.html` — Canvas-based visualization (replaces SVG rendering)
- API endpoints serving from existing SQLite databases

## API Endpoints

All endpoints return JSON. Server reads fresh from SQLite on each request — no caching layer.

### `GET /`
Serves `bin/static/index.html`.

### `GET /api/nodes`
Returns all decision nodes with metadata.

```json
{
  "nodes": [
    {
      "id": "ADR-001",
      "title": "Use MobX for State Management",
      "status": "accepted",
      "date": "2026-04-27",
      "tags": ["frontend", "state-management"],
      "project": "sempl-core/ui",
      "file": "decisions/ADR-001-use-mobx-for-state.md"
    }
  ],
  "total": 108
}
```

Query params:
- `?tag=frontend` — filter by tag
- `?status=accepted` — filter by status
- `?project=sempl-core` — filter by project prefix
- `?limit=500&offset=0` — pagination (default: all)

### `GET /api/links`
Returns all relationship edges.

```json
{
  "links": [
    { "source": "ADR-005", "target": "ADR-001", "relation": "supersedes" }
  ],
  "total": 170
}
```

Query params:
- `?node=ADR-001` — links touching this node only
- `?relation=supersedes` — filter by relation type

### `GET /api/search?q=<query>`
Proxies to FTS5 search. Returns matching node IDs + rank for highlighting.

```json
{
  "query": "state management",
  "results": [
    { "id": "ADR-001", "title": "Use MobX...", "rank": -2.45, "snippet": "..." }
  ],
  "count": 3
}
```

### `GET /api/tags`
Returns all unique tags with counts.

```json
{
  "tags": [
    { "name": "frontend", "count": 12 },
    { "name": "infrastructure", "count": 8 }
  ]
}
```

### `GET /api/stats`
Summary for UI header.

```json
{
  "nodes": 108,
  "links": 170,
  "tags": 15,
  "statuses": { "accepted": 80, "proposed": 20, "superseded": 8 }
}
```

## Server Implementation

### `lib/router.py` — Minimal HTTP Router

stdlib `http.server.BaseHTTPRequestHandler` with a route registry. ~50 lines.

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

class Router:
    def __init__(self):
        self._routes = {}
    
    def route(self, path):
        def decorator(fn):
            self._routes[path] = fn
            return fn
        return decorator
    
    def match(self, path):
        return self._routes.get(path)

class APIHandler(BaseHTTPRequestHandler):
    router = None       # set before serving
    static_dir = None   # set before serving
    
    def do_GET(self):
        parsed = urlparse(self.path)
        handler = self.router.match(parsed.path)
        if handler:
            params = parse_qs(parsed.query)
            result = handler(params)
            self._json_response(result)
        elif parsed.path == '/':
            self._serve_file('index.html', 'text/html')
        else:
            self.send_error(404)
    
    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def _serve_file(self, filename, content_type):
        filepath = Path(self.static_dir) / filename
        if filepath.exists():
            body = filepath.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass  # silence request logs
```

### `cmd_serve()` in `decision-engine.py`

New subcommand. Wires routes to existing DB query functions.

```python
def cmd_serve(port=8877):
    router = Router()

    @router.route('/api/nodes')
    def nodes(params): ...  # query graph.db objects + parse ADR metadata

    @router.route('/api/links')
    def links(params): ...  # query graph.db relations

    @router.route('/api/search')
    def search(params): ...  # proxy to FTS5

    @router.route('/api/tags')
    def tags(params): ...    # aggregate from nodes

    @router.route('/api/stats')
    def stats(params): ...   # counts

    APIHandler.router = router
    APIHandler.static_dir = SCRIPT_DIR / 'static'
    
    server = HTTPServer(('localhost', port), APIHandler)
    print(json.dumps({"serving": f"http://localhost:{port}", "nodes": count}))
    server.serve_forever()
```

Usage:
```bash
python bin/decision-engine.py serve            # default port 8877
python bin/decision-engine.py serve --port 9000
python bin/decision-engine.py serve --open     # also opens browser
```

Port 8877 chosen to avoid conflicts with Django (8000), Vite (5173), and common dev ports.

## Canvas Renderer (`bin/static/index.html`)

### Layout Engine
**d3-force** — identical simulation configuration to current SVG version:

```javascript
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id).distance(45).strength(0.9))
  .force('charge', d3.forceManyBody().strength(-80).distanceMax(baseRadius * 2))
  .force('center', d3.forceCenter(0, 0).strength(0.3))
  .force('radial', d3.forceRadial(baseRadius * 0.6, 0, 0).strength(0.15))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 3).strength(0.7))
  .force('tagCluster', tagCluster)
  .alphaDecay(0.008)
  .velocityDecay(0.4);
```

### Rendering: Canvas 2D (not SVG)

Why: SVG creates DOM elements per node. At 2000 nodes = 6000+ DOM elements (node + glow + label). Browser chokes. Canvas draws to a single bitmap — same visual output, constant DOM overhead.

```javascript
// Draw loop (called on each simulation tick)
function draw() {
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  
  // Links
  links.forEach(drawLink);
  
  // Nodes (glow → circle → optional label)
  nodes.forEach(drawNode);
  
  ctx.restore();
}
```

### Hit Detection: d3-quadtree

Canvas has no DOM events per-element. Use spatial index:

```javascript
const quadtree = d3.quadtree()
  .x(d => d.x)
  .y(d => d.y)
  .addAll(nodes);

canvas.on('mousemove', (event) => {
  const [mx, my] = transform.invert([event.offsetX, event.offsetY]);
  const nearest = quadtree.find(mx, my, 20); // 20px radius
  if (nearest !== hoveredNode) {
    hoveredNode = nearest;
    draw(); // redraw with highlight
  }
});
```

Quadtree rebuilt on each tick (cheap — O(n log n)).

### Zoom/Pan: d3-zoom

Same as current SVG version, but applied to canvas transform:

```javascript
const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on('zoom', (event) => {
    transform = event.transform;
    draw();
  });
d3.select(canvas).call(zoom);
```

### Visual Aesthetic (preserve exactly)

| Element | Current (SVG) | New (Canvas) |
|---------|---------------|-------------|
| Background | `#0a0a0f` | Same |
| Node glow | `circle` with opacity 0.15, r+4 | `arc()` with `shadowBlur: 8` |
| Node circle | `circle` opacity 0.85 | `arc()` with `globalAlpha: 0.85` |
| Node color | Primary tag → TAG_PALETTE | Same palette, same logic |
| Node size | `2.5 + connectionCount * 1` | Same formula |
| Link color | RELATION_COLORS map | Same map |
| Link arrows | SVG `<marker>` | Canvas arrow heads (small triangle at endpoint) |
| Labels | Hidden, shown on hover for neighbors | Same behavior, Canvas `fillText()` |
| Info panel | HTML overlay, right side | Same HTML panel (outside canvas) |
| Legend | HTML overlay, bottom-left | Same HTML (outside canvas) |
| Title | HTML overlay, top-left | Same HTML (outside canvas) |

### Search UI (new feature)

Search bar in top-left (below title). Types query → debounced fetch to `/api/search?q=` → matching nodes glow brighter, non-matching dim.

```html
<input id="search-input" type="text" placeholder="Search decisions..." />
```

```javascript
searchInput.addEventListener('input', debounce(async (e) => {
  const q = e.target.value.trim();
  if (!q) { clearSearch(); return; }
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
  const data = await res.json();
  searchHits = new Set(data.results.map(r => r.id));
  draw(); // redraw with search highlighting
}, 300));
```

In `drawNode()`:
```javascript
if (searchHits.size > 0) {
  const isHit = searchHits.has(node.id);
  ctx.globalAlpha = isHit ? 1.0 : 0.1;
  // hit nodes also get label drawn
}
```

### Data Loading

On page load, fetch all data:

```javascript
async function loadGraph() {
  const [nodesRes, linksRes, statsRes] = await Promise.all([
    fetch('/api/nodes'),
    fetch('/api/links'),
    fetch('/api/stats'),
  ]);
  // parse, init simulation, start draw loop
}
```

For 2000+ nodes: initial load is fine (JSON payload ~500KB). If 10k+ becomes real, add viewport-based loading — but don't build it now.

### Drag Behavior

Canvas drag needs manual implementation since there's no DOM element to attach to:

```javascript
let draggedNode = null;

canvas.on('mousedown', (event) => {
  const [mx, my] = screenToWorld(event);
  draggedNode = quadtree.find(mx, my, 20);
  if (draggedNode) {
    simulation.alphaTarget(0.1).restart();
    draggedNode.fx = draggedNode.x;
    draggedNode.fy = draggedNode.y;
  }
});

canvas.on('mousemove', (event) => {
  if (draggedNode) {
    const [mx, my] = screenToWorld(event);
    draggedNode.fx = mx;
    draggedNode.fy = my;
  }
});

canvas.on('mouseup', () => {
  if (draggedNode) {
    simulation.alphaTarget(0);
    draggedNode.fx = null;
    draggedNode.fy = null;
    draggedNode = null;
  }
});
```

## Project Structure (additions only)

```
frontier-brain/
├── bin/
│   ├── decision-engine.py     # + serve command, + API route handlers
│   ├── visualize.py           # UNCHANGED — offline static fallback
│   └── static/
│       └── index.html         # Canvas-based visualization
├── lib/
│   ├── graphdb/               # UNCHANGED
│   └── router.py              # Minimal stdlib HTTP router
└── decisions/
    ├── graph.db               # UNCHANGED (gitignored, derived)
    └── search.db              # UNCHANGED (gitignored, derived)
```

Total new files: 2 (`lib/router.py`, `bin/static/index.html`)
Modified files: 1 (`bin/decision-engine.py` — add `serve` command)

## Code Style

- Python: match existing `decision-engine.py` — no type annotations on locals, `Path` for paths, `json.dumps` for output
- JavaScript: match existing `visualize.py` HTML template — vanilla JS, no modules, d3 from CDN
- No comments unless the WHY is non-obvious
- No docstrings beyond module-level one-liners

## CDN Dependencies (loaded by index.html)

Same as current SVG version:
- `d3.v7.min.js` — force simulation, zoom, quadtree, scales

No new external dependencies.

## Testing Strategy

### Manual verification (primary)
1. `python bin/decision-engine.py index` — rebuild DBs
2. `python bin/decision-engine.py serve --open` — opens browser
3. Verify: sphere shape, tag clustering, Obsidian dark theme
4. Verify: hover highlights neighbors, click opens info panel
5. Verify: drag nodes, zoom/pan, search highlights matches
6. Verify: 108 nodes render smoothly (compare to SVG version)

### Stress test
1. Generate 2000 skeleton ADRs (script in `bin/generate-test-adrs.py`)
2. `python bin/decision-engine.py index && python bin/decision-engine.py serve --open`
3. Verify: loads in <3s, simulation runs at 30+ fps, zoom/pan smooth
4. Clean up test ADRs after

### API smoke tests
```bash
# After `serve` is running:
curl localhost:8877/api/nodes | python -m json.tool
curl localhost:8877/api/links | python -m json.tool
curl "localhost:8877/api/search?q=state+management" | python -m json.tool
curl localhost:8877/api/tags | python -m json.tool
curl localhost:8877/api/stats | python -m json.tool
curl "localhost:8877/api/nodes?tag=frontend" | python -m json.tool
```

## Boundaries

### Always do
- Read fresh from SQLite on each API request (no stale cache)
- Preserve exact force simulation parameters (sphere shape + tag clustering)
- Preserve Obsidian dark aesthetic (colors, glow, background)
- Keep `visualize.py` working as offline fallback
- Keep server session-scoped (dies with Ctrl+C)
- Output startup JSON to stdout (matches existing CLI pattern)

### Ask first about
- Adding WebSocket for live push updates
- Adding new Python dependencies
- Changing force simulation parameters
- Adding viewport-based lazy loading (only if 2000+ proves insufficient)
- Changing default port from 8877

### Never do
- Install npm/Node dependencies for the visualization
- Make the server a persistent daemon or systemd service
- Add authentication/sessions
- Modify existing `visualize.py` behavior
- Cache API responses (DBs are small, reads are fast)
- Add a build step for the frontend (no bundlers, no transpilers)

## ADR Reference

This spec aligns with:
- **ADR-001**: Hybrid graph + FTS5 — server exposes both indexes via API
- **ADR-002**: Zero external deps — stdlib http.server, no Flask/FastAPI
- **ADR-003**: Autonomous recording — `index` rebuilds, `serve` reads fresh
- **ADR-007**: Markdown source of truth — databases remain derived, server reads derived DBs

## Implementation Order

1. **`lib/router.py`** — HTTP router class (testable standalone)
2. **`cmd_serve()` in `decision-engine.py`** — wire routes, serve static files
3. **`bin/static/index.html`** — Canvas renderer (port visual logic from SVG template)
4. **Search UI** — add search bar + FTS5 highlighting
5. **Stress test** — generate 2000 nodes, verify performance

Each step independently verifiable. Step 3 is the bulk of the work.
