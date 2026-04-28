#!/usr/bin/env python3
"""
Generate an interactive force-directed graph visualization of the decision knowledge graph.
Reads from brain.db, outputs standalone HTML with inlined d3.

Usage:
    python bin/visualize.py                    # writes ~/.claude/decisions/graph.html
    python bin/visualize.py --open             # writes and opens in browser
    python bin/visualize.py -o out.html        # custom output path
"""

import argparse
import json
import sqlite3
import webbrowser
from pathlib import Path

DECISIONS_DIR = Path.home() / ".claude" / "decisions"
DB_PATH = DECISIONS_DIR / "brain.db"
D3_PATH = Path(__file__).resolve().parent / "static" / "d3.v7.min.js"


def collect_graph_data() -> dict:
    if not DB_PATH.exists():
        return {"nodes": [], "links": [], "projects": []}

    conn = sqlite3.connect(str(DB_PATH))

    rows = conn.execute(
        "SELECT id, title, type, status, date, project, tags_json, affects_json, recorded_by FROM decisions"
    ).fetchall()

    nodes = []
    projects = set()
    for row in rows:
        project = row[5] or ""
        if project:
            projects.add(project)
        nodes.append({
            "id": row[0],
            "title": row[1],
            "type": row[2],
            "status": row[3],
            "date": row[4] or "",
            "project": project,
            "tags": json.loads(row[6] or "[]"),
            "affects": json.loads(row[7] or "[]"),
            "recorded_by": row[8] or "",
        })

    rels = conn.execute(
        "SELECT source_id, target_id, relation_type FROM relationships"
    ).fetchall()

    seen_edges = set()
    links = []
    for src, tgt, rel_type in rels:
        if rel_type == "superseded_by":
            continue
        if rel_type == "related_to" and src > tgt:
            continue
        key = (src, tgt, rel_type)
        if key not in seen_edges:
            seen_edges.add(key)
            links.append({"source": src, "target": tgt, "relation": rel_type})

    conn.close()
    return {"nodes": nodes, "links": links, "projects": sorted(projects)}


def load_d3() -> str:
    if D3_PATH.exists():
        return D3_PATH.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Vendored d3 not found at {D3_PATH}. Run from repo or install.")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision Knowledge Graph</title>
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
  }

  #graph-container {
    position: absolute;
    inset: 0;
  }

  svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .link {
    stroke-opacity: 0.3;
    stroke-width: 1.2;
  }
  .link-supersedes {
    stroke-dasharray: 6 3;
  }

  .node-shape {
    cursor: grab;
    transition: opacity 0.15s;
  }
  .node-shape:hover {
    filter: brightness(1.4);
  }

  .node-label {
    font-size: 10px;
    fill: #c9d1d9;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: hanging;
    text-shadow: 0 0 6px #0d1117, 0 0 12px #0d1117, 0 0 3px #0d1117;
    opacity: 0;
    transition: opacity 0.15s;
  }

  /* Tooltip */
  #tooltip {
    position: fixed;
    display: none;
    padding: 10px 14px;
    background: rgba(22, 27, 34, 0.95);
    border: 1px solid rgba(139, 148, 158, 0.3);
    border-radius: 8px;
    font-size: 12px;
    color: #c9d1d9;
    pointer-events: none;
    z-index: 100;
    max-width: 320px;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }
  #tooltip .tt-title {
    font-weight: 600;
    font-size: 13px;
    color: #f0f6fc;
    margin-bottom: 4px;
  }
  #tooltip .tt-id {
    font-size: 10px;
    color: #58a6ff;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
  }
  #tooltip .tt-row {
    display: flex;
    justify-content: space-between;
    padding: 2px 0;
    gap: 12px;
  }
  #tooltip .tt-label { color: #8b949e; }
  #tooltip .tt-value { color: #c9d1d9; font-weight: 500; }
  #tooltip .tt-tag {
    display: inline-block;
    background: rgba(88, 166, 255, 0.1);
    color: #58a6ff;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 8px;
    margin: 1px 2px 1px 0;
  }

  /* Title + count */
  #title {
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 10;
    font-size: 13px;
    color: rgba(201,209,217,0.5);
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  #title span { color: #58a6ff; }
  #node-count {
    font-size: 11px;
    color: rgba(201,209,217,0.3);
    margin-top: 4px;
  }

  /* Info panel */
  #info-panel {
    position: relative;
    max-height: 55vh;
    padding: 20px;
    overflow-y: auto;
    display: none;
    background: rgba(22, 27, 34, 0.92);
    border: 1px solid rgba(139, 148, 158, 0.2);
    border-radius: 12px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  #info-panel.visible { display: block; }
  #info-panel h2 {
    font-size: 14px;
    color: #f0f6fc;
    margin-bottom: 4px;
    font-weight: 600;
  }
  #info-panel .panel-id {
    font-size: 10px;
    color: #58a6ff;
    margin-bottom: 10px;
    font-weight: 600;
    letter-spacing: 0.15em;
  }
  #info-panel .meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 3px 0;
    border-bottom: 1px solid rgba(139,148,158,0.1);
  }
  #info-panel .meta-label { color: #8b949e; }
  #info-panel .meta-value { color: #c9d1d9; font-weight: 500; }
  #info-panel .tag {
    display: inline-block;
    background: rgba(88, 166, 255, 0.1);
    color: #58a6ff;
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 8px;
    margin: 2px 3px 2px 0;
  }
  #info-panel .tags-row { margin-top: 8px; }
  #info-panel .connections { margin-top: 12px; font-size: 12px; }
  #info-panel .connections h3 {
    font-size: 10px;
    color: #58a6ff;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 600;
  }
  #info-panel .conn-item {
    padding: 3px 0;
    color: #c9d1d9;
    cursor: pointer;
  }
  #info-panel .conn-item:hover { color: #58a6ff; }
  #info-panel .conn-rel {
    color: #8b949e;
    font-size: 10px;
    margin-right: 6px;
  }
  #info-panel .close-btn {
    position: absolute; top: 14px; right: 16px;
    background: none; border: none;
    color: #8b949e; font-size: 18px;
    cursor: pointer; line-height: 1;
  }
  #info-panel .close-btn:hover { color: #58a6ff; }

  .type-badge {
    display: inline-block; font-size: 10px;
    padding: 2px 8px; border-radius: 8px;
    font-weight: 600; letter-spacing: 0.3px;
  }
  .type-decision { background: rgba(88,166,255,0.12); color: #58a6ff; }
  .type-knowledge { background: rgba(210,153,34,0.12); color: #d29922; }
  .type-context { background: rgba(63,185,80,0.12); color: #3fb950; }

  /* Right column: legend + info panel */
  #right-column {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 10;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: calc(100vh - 32px);
    width: 280px;
    pointer-events: none;
  }
  #right-column > * { pointer-events: auto; }

  /* Legend panel */
  #legend {
    background: rgba(22, 27, 34, 0.88);
    border: 1px solid rgba(139, 148, 158, 0.15);
    border-radius: 10px;
    padding: 12px 14px;
    backdrop-filter: blur(12px);
    font-size: 11px;
  }
  #legend h3 {
    font-size: 9px;
    color: #58a6ff;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 600;
    margin-bottom: 5px;
    margin-top: 8px;
  }
  #legend h3:first-child { margin-top: 0; }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 1.5px 0;
    color: #c9d1d9;
    font-size: 11px;
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .legend-shape {
    width: 14px;
    text-align: center;
    flex-shrink: 0;
    font-size: 12px;
    line-height: 1;
  }
  .legend-line {
    display: inline-block;
    width: 20px;
    height: 0;
    border-top: 2px solid #8b949e;
    vertical-align: middle;
    flex-shrink: 0;
  }
  .legend-line-dashed {
    border-top-style: dashed;
    border-top-color: #f85149;
  }

  /* Filter sidebar */
  #filter-sidebar {
    position: fixed;
    top: 70px;
    left: 0;
    z-index: 10;
    background: rgba(22, 27, 34, 0.92);
    border: 1px solid rgba(139, 148, 158, 0.15);
    border-left: none;
    border-radius: 0 10px 10px 0;
    padding: 12px 14px 12px 12px;
    backdrop-filter: blur(12px);
    font-size: 11px;
    max-height: calc(100vh - 86px);
    overflow-y: auto;
    transition: transform 0.3s ease;
    min-width: 170px;
  }
  #filter-sidebar.collapsed {
    transform: translateX(calc(-100% + 28px));
  }
  #filter-sidebar.collapsed .filter-content {
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
  }
  .filter-content {
    opacity: 1;
    transition: opacity 0.2s ease 0.1s;
  }
  #filter-toggle {
    position: absolute;
    top: 8px;
    right: 6px;
    background: none;
    border: none;
    color: #8b949e;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 4px;
    line-height: 1;
    z-index: 1;
  }
  #filter-toggle:hover { color: #58a6ff; }
  .filter-section h4 {
    font-size: 9px;
    color: #58a6ff;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 600;
    margin-bottom: 4px;
    margin-top: 10px;
  }
  .filter-section:first-child h4 { margin-top: 0; }
  .filter-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 4px;
  }
  .filter-actions button {
    background: none;
    border: none;
    color: #58a6ff;
    font-size: 10px;
    cursor: pointer;
    padding: 0;
  }
  .filter-actions button:hover { color: #79c0ff; }
  .filter-cb {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 0;
    cursor: pointer;
    color: #c9d1d9;
    font-size: 11px;
  }
  .filter-cb input[type="checkbox"] {
    accent-color: #58a6ff;
    cursor: pointer;
    margin: 0;
  }
  .filter-cb .cb-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
</style>
</head>
<body>

<div id="title">
  <span>&#9670;</span> Decision Knowledge Graph
  <div id="node-count"></div>
</div>

<div id="tooltip"></div>

<div id="filter-sidebar">
  <button id="filter-toggle" onclick="toggleFilter()">&#9666;</button>
  <div class="filter-content" id="filter-content"></div>
</div>

<div id="graph-container">
  <svg id="graph-svg">
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
      <marker id="arrow-supersedes" viewBox="0 0 10 6" refX="10" refY="3"
              markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,3 L0,6" fill="#f85149" opacity="0.6"/>
      </marker>
    </defs>
  </svg>
</div>

<div id="right-column">
  <div id="legend"></div>
  <div id="info-panel">
    <button class="close-btn" onclick="closePanel()">&times;</button>
    <div id="panel-content"></div>
  </div>
</div>

<script>
__D3_INLINE__
</script>
<script>
const DATA = __GRAPH_DATA__;

const PROJECT_PALETTE = [
  '#58a6ff', '#f0883e', '#a371f7', '#3fb950', '#f778ba',
  '#d29922', '#79c0ff', '#56d4dd', '#db61a2', '#7ee787',
  '#e3b341', '#bc8cff', '#ff7b72', '#ffa657', '#d2a8ff',
];

const projectColorMap = {};
DATA.projects.forEach((p, i) => {
  projectColorMap[p] = PROJECT_PALETTE[i % PROJECT_PALETTE.length];
});

function projectColor(d) {
  return projectColorMap[d.project] || '#8b949e';
}

const RELATION_COLORS = {
  supersedes: '#f85149',
  related_to: '#8b949e',
};

// Custom hexagon symbol for context type
const hexagonSymbol = {
  draw(ctx, size) {
    const r = Math.sqrt(size / (1.5 * Math.sqrt(3)));
    const step = Math.PI / 3;
    ctx.moveTo(r, 0);
    for (let i = 1; i < 6; i++) {
      ctx.lineTo(r * Math.cos(step * i), r * Math.sin(step * i));
    }
    ctx.closePath();
  }
};

const SHAPE_TYPE = {
  decision:  d3.symbolCircle,
  knowledge: d3.symbolDiamond,
  context:   hexagonSymbol,
};

// Connection count for sizing
const connectionCount = {};
DATA.nodes.forEach(n => connectionCount[n.id] = 0);
DATA.links.forEach(l => {
  connectionCount[l.source] = (connectionCount[l.source] || 0) + 1;
  connectionCount[l.target] = (connectionCount[l.target] || 0) + 1;
});

function nodeSize(d) {
  const count = connectionCount[d.id] || 0;
  return 40 + count * 15;
}

DATA.nodes.forEach(n => { n._visible = true; });
DATA.links.forEach(l => { l._visible = true; });
let currentHighlight = null;

document.getElementById('node-count').textContent =
  DATA.nodes.length + ' records \\u00b7 ' + DATA.links.length + ' connections';

const svg = d3.select('#graph-svg');
const container = svg.append('g');

const zoom = d3.zoom()
  .scaleExtent([0.15, 6])
  .on('zoom', (event) => container.attr('transform', event.transform));
svg.call(zoom);

const width = window.innerWidth;
const height = window.innerHeight;
svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2));

const nodeCount = DATA.nodes.length;
const chargeStr = nodeCount > 200 ? -60 : nodeCount > 50 ? -120 : -200;
const linkDist = nodeCount > 200 ? 40 : nodeCount > 50 ? 60 : 90;

const simulation = d3.forceSimulation(DATA.nodes)
  .force('link', d3.forceLink(DATA.links).id(d => d.id).distance(linkDist).strength(0.4))
  .force('charge', d3.forceManyBody().strength(chargeStr))
  .force('center', d3.forceCenter(0, 0).strength(0.1))
  .force('collision', d3.forceCollide().radius(d => Math.sqrt(nodeSize(d) / Math.PI) + 4).strength(0.6))
  .alphaDecay(0.025)
  .velocityDecay(0.4);

// Links
const linkGroup = container.append('g');
const link = linkGroup.selectAll('line')
  .data(DATA.links)
  .join('line')
  .attr('class', d => 'link' + (d.relation === 'supersedes' ? ' link-supersedes' : ''))
  .attr('stroke', d => RELATION_COLORS[d.relation] || '#8b949e')
  .attr('marker-end', d => d.relation === 'supersedes' ? 'url(#arrow-supersedes)' : null);

// Nodes
const nodeGroup = container.append('g');
const node = nodeGroup.selectAll('g')
  .data(DATA.nodes)
  .join('g')
  .attr('class', 'node-group');

// Glow behind shape
node.append('path')
  .attr('d', d => {
    const sym = SHAPE_TYPE[d.type] || d3.symbolCircle;
    return d3.symbol().type(sym).size(nodeSize(d) * 3)();
  })
  .attr('fill', d => projectColor(d))
  .attr('opacity', 0.12)
  .attr('filter', 'url(#glow)');

// Main shape
node.append('path')
  .attr('d', d => {
    const sym = SHAPE_TYPE[d.type] || d3.symbolCircle;
    return d3.symbol().type(sym).size(nodeSize(d))();
  })
  .attr('fill', d => projectColor(d))
  .attr('opacity', 0.85)
  .attr('stroke', d => projectColor(d))
  .attr('stroke-width', 1.2)
  .attr('stroke-opacity', 0.4)
  .attr('class', 'node-shape');

// Labels
node.append('text')
  .attr('class', 'node-label')
  .attr('dy', d => Math.sqrt(nodeSize(d) / Math.PI) + 12)
  .text(d => d.title.length > 30 ? d.title.slice(0, 28) + '\\u2026' : d.title);

// Drag
node.call(d3.drag()
  .on('start', (event, d) => {
    if (!event.active) simulation.alphaTarget(0.1).restart();
    d.fx = d.x; d.fy = d.y;
  })
  .on('drag', (event, d) => {
    d.fx = event.x; d.fy = event.y;
  })
  .on('end', (event, d) => {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  })
);

// Tooltip
const tooltip = document.getElementById('tooltip');

node.on('mouseenter', (event, d) => {
  highlightNode(d);
  let html = `<div class="tt-id">#${d.id} &middot; ${d.type}</div>`;
  html += `<div class="tt-title">${d.title}</div>`;
  html += `<div class="tt-row"><span class="tt-label">Project</span><span class="tt-value">${d.project || 'none'}</span></div>`;
  html += `<div class="tt-row"><span class="tt-label">Status</span><span class="tt-value">${d.status}</span></div>`;
  html += `<div class="tt-row"><span class="tt-label">Date</span><span class="tt-value">${d.date}</span></div>`;
  if (d.recorded_by) {
    html += `<div class="tt-row"><span class="tt-label">By</span><span class="tt-value">${d.recorded_by}</span></div>`;
  }
  if (d.tags && d.tags.length) {
    html += '<div style="margin-top:4px">' + d.tags.map(t => `<span class="tt-tag">${t}</span>`).join('') + '</div>';
  }
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  tooltip.style.left = (event.clientX + 14) + 'px';
  tooltip.style.top = (event.clientY - 10) + 'px';
}).on('mousemove', (event) => {
  tooltip.style.left = (event.clientX + 14) + 'px';
  tooltip.style.top = (event.clientY - 10) + 'px';
}).on('mouseleave', () => {
  tooltip.style.display = 'none';
  if (!document.getElementById('info-panel').classList.contains('visible')) {
    clearHighlight();
  }
});

// Click for info panel
node.on('click', (event, d) => {
  event.stopPropagation();
  showPanel(d);
  highlightNode(d);
});
svg.on('click', () => {
  closePanel();
  clearHighlight();
});

function highlightNode(d) {
  currentHighlight = d;
  const connected = new Set();
  DATA.links.forEach(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === d.id) connected.add(tid);
    if (tid === d.id) connected.add(sid);
  });
  connected.add(d.id);

  node.select('.node-shape')
    .attr('opacity', n => connected.has(n.id) ? 1 : 0.12);
  node.select('.node-label')
    .attr('opacity', n => connected.has(n.id) ? 0.9 : 0);

  link.attr('stroke-opacity', l => {
    if (!l._visible) return 0;
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 0.7 : 0.05;
  }).attr('stroke-width', l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 2 : 1.2;
  });
}

function clearHighlight() {
  currentHighlight = null;
  node.select('.node-shape').attr('opacity', d => d._visible ? 0.85 : 0);
  node.select('.node-label').attr('opacity', 0);
  link.attr('stroke-opacity', l => l._visible ? 0.3 : 0).attr('stroke-width', 1.2);
}

function showPanel(d) {
  const panel = document.getElementById('info-panel');
  const connected = [];
  DATA.links.forEach(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === d.id) connected.push({ id: tid, relation: l.relation, dir: 'out' });
    if (tid === d.id) connected.push({ id: sid, relation: l.relation, dir: 'in' });
  });

  const typeClass = 'type-' + (d.type || 'decision');
  let html = `
    <div class="panel-id">#${d.id}</div>
    <h2>${d.title}</h2>
    <div style="margin: 6px 0">
      <span class="type-badge ${typeClass}">${d.type}</span>
    </div>
    <div class="meta-row"><span class="meta-label">Status</span><span class="meta-value">${d.status}</span></div>
    <div class="meta-row"><span class="meta-label">Date</span><span class="meta-value">${d.date}</span></div>
    <div class="meta-row"><span class="meta-label">Project</span><span class="meta-value">${d.project || 'none'}</span></div>
    <div class="meta-row"><span class="meta-label">Recorded by</span><span class="meta-value">${d.recorded_by || 'unknown'}</span></div>
  `;

  if (d.tags && d.tags.length) {
    html += '<div class="tags-row">' + d.tags.map(t => `<span class="tag">${t}</span>`).join('') + '</div>';
  }
  if (d.affects && d.affects.length) {
    html += `<div class="meta-row"><span class="meta-label">Affects</span><span class="meta-value">${d.affects.join(', ')}</span></div>`;
  }

  if (connected.length > 0) {
    html += '<div class="connections"><h3>Connections</h3>';
    connected.forEach(c => {
      const relColor = RELATION_COLORS[c.relation] || '#8b949e';
      const arrow = c.dir === 'out' ? '&rarr;' : '&larr;';
      const target = DATA.nodes.find(n => n.id === c.id);
      const label = target ? target.title : '#' + c.id;
      html += `<div class="conn-item" onclick="focusNode(${c.id})">
        <span class="conn-rel" style="color:${relColor}">${c.relation} ${arrow}</span> ${label}
      </div>`;
    });
    html += '</div>';
  }

  document.getElementById('panel-content').innerHTML = html;
  panel.classList.add('visible');
}

function closePanel() {
  document.getElementById('info-panel').classList.remove('visible');
}

function focusNode(id) {
  const d = DATA.nodes.find(n => n.id === id);
  if (d) {
    showPanel(d);
    highlightNode(d);
  }
}

// Legend panel
(function buildLegend() {
  const el = document.getElementById('legend');
  let h = '<h3>Projects</h3>';
  DATA.projects.forEach(p => {
    h += '<div class="legend-item"><span class="legend-dot" style="background:' + (projectColorMap[p] || '#8b949e') + '"></span>' + p + '</div>';
  });
  if (DATA.nodes.some(n => !n.project)) {
    h += '<div class="legend-item"><span class="legend-dot" style="background:#8b949e"></span><em>none</em></div>';
  }
  h += '<h3>Types</h3>';
  h += '<div class="legend-item"><span class="legend-shape">&#9679;</span>decision</div>';
  h += '<div class="legend-item"><span class="legend-shape">&#9670;</span>knowledge</div>';
  h += '<div class="legend-item"><span class="legend-shape">&#11041;</span>context</div>';
  h += '<h3>Edges</h3>';
  h += '<div class="legend-item"><span class="legend-line"></span>related</div>';
  h += '<div class="legend-item"><span class="legend-line legend-line-dashed"></span>supersedes</div>';
  el.innerHTML = h;
})();

// Filter sidebar
const allProjects = [...DATA.projects];
if (DATA.nodes.some(n => !n.project)) allProjects.push('');
const allTypes = ['decision', 'knowledge', 'context'];
const activeProjects = new Set(allProjects);
const activeTypes = new Set(allTypes);

(function buildFilters() {
  const el = document.getElementById('filter-content');
  const icons = { decision: '&#9679;', knowledge: '&#9670;', context: '&#11041;' };
  let h = '<div class="filter-section"><h4>Projects</h4>';
  h += '<div class="filter-actions"><button onclick="toggleAll(\'project\',true)">All</button><button onclick="toggleAll(\'project\',false)">None</button></div>';
  allProjects.forEach(p => {
    const c = projectColorMap[p] || '#8b949e';
    h += '<label class="filter-cb"><input type="checkbox" checked data-filter="project" data-value="' + p + '"><span class="cb-dot" style="background:' + c + '"></span>' + (p || '<em>none</em>') + '</label>';
  });
  h += '</div><div class="filter-section"><h4>Types</h4>';
  h += '<div class="filter-actions"><button onclick="toggleAll(\'type\',true)">All</button><button onclick="toggleAll(\'type\',false)">None</button></div>';
  allTypes.forEach(t => {
    h += '<label class="filter-cb"><input type="checkbox" checked data-filter="type" data-value="' + t + '"><span style="width:14px;text-align:center;font-size:11px">' + icons[t] + '</span>' + t + '</label>';
  });
  h += '</div>';
  el.innerHTML = h;
  el.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.addEventListener('change', onFilterChange));
})();

function onFilterChange(e) {
  const cb = e.target;
  const set = cb.dataset.filter === 'project' ? activeProjects : activeTypes;
  if (cb.checked) set.add(cb.dataset.value); else set.delete(cb.dataset.value);
  applyFilters();
}
function toggleAll(kind, on) {
  const set = kind === 'project' ? activeProjects : activeTypes;
  const vals = kind === 'project' ? allProjects : allTypes;
  set.clear(); if (on) vals.forEach(v => set.add(v));
  document.querySelectorAll('input[data-filter="' + kind + '"]').forEach(cb => { cb.checked = on; });
  applyFilters();
}
function toggleFilter() {
  const sb = document.getElementById('filter-sidebar');
  sb.classList.toggle('collapsed');
  document.getElementById('filter-toggle').innerHTML = sb.classList.contains('collapsed') ? '&#9776;' : '&#9666;';
}
function isNodeVisible(d) {
  return activeProjects.has(d.project || '') && activeTypes.has(d.type);
}
function applyFilters() {
  const visibleIds = new Set();
  DATA.nodes.forEach(n => { n._visible = isNodeVisible(n); if (n._visible) visibleIds.add(n.id); });
  DATA.links.forEach(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    l._visible = visibleIds.has(sid) && visibleIds.has(tid);
  });
  node.transition().duration(300)
    .style('opacity', d => d._visible ? 1 : 0)
    .style('pointer-events', d => d._visible ? 'all' : 'none');
  link.transition().duration(300)
    .attr('stroke-opacity', l => l._visible ? 0.3 : 0);
  if (currentHighlight && !currentHighlight._visible) {
    closePanel(); currentHighlight = null;
  } else if (currentHighlight) {
    highlightNode(currentHighlight);
  }
  const vis = visibleIds.size, total = DATA.nodes.length;
  document.getElementById('node-count').textContent =
    vis === total ? total + ' records \\u00b7 ' + DATA.links.length + ' connections'
                  : 'showing ' + vis + ' of ' + total + ' records';
  simulation.alpha(0.3).restart();
}

simulation.on('tick', () => {
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  node.attr('transform', d => `translate(${d.x},${d.y})`);
});

window.addEventListener('resize', () => {
  simulation.force('center', d3.forceCenter(0, 0));
  simulation.alpha(0.1).restart();
});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Visualize the decision knowledge graph")
    parser.add_argument("-o", "--output", default=str(DECISIONS_DIR / "graph.html"))
    parser.add_argument("--open", action="store_true", help="Open in browser after generating")
    args = parser.parse_args()

    data = collect_graph_data()
    d3_code = load_d3()

    html = HTML_TEMPLATE.replace("__D3_INLINE__", d3_code)
    html = html.replace("__GRAPH_DATA__", json.dumps(data, indent=2))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(json.dumps({"output": str(output_path), "nodes": len(data["nodes"]), "links": len(data["links"])}))

    if args.open:
        webbrowser.open(f"file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
