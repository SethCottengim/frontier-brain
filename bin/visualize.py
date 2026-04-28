#!/usr/bin/env python3
"""
Generate an interactive force-directed graph visualization of the decision knowledge graph.
Outputs a standalone HTML file using d3-force with Obsidian-style dark theme.

Usage:
    python bin/visualize.py                    # writes decisions/graph.html
    python bin/visualize.py --open             # writes and opens in browser
    python bin/visualize.py -o out.html        # custom output path
"""

import json
import os
import sys
import webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DECISIONS_DIR = PROJECT_DIR / "decisions"

sys.path.insert(0, str(PROJECT_DIR / "lib"))

import yaml
from graphdb import GraphDB


def collect_graph_data() -> dict:
    adrs = []
    for f in sorted(DECISIONS_DIR.glob("ADR-*.md")):
        text = f.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if not meta or "id" not in meta:
            continue
        adrs.append(meta)

    nodes = []
    tag_set = set()
    for adr in adrs:
        tags = adr.get("tags", []) or []
        for t in tags:
            tag_set.add(t)
        nodes.append({
            "id": adr["id"],
            "title": adr.get("title", ""),
            "status": adr.get("status", "proposed"),
            "date": str(adr.get("date", "")),
            "tags": tags,
            "project": adr.get("project", ""),
            "file": str(f.name),
        })

    graph_path = DECISIONS_DIR / "graph.db"
    links = []
    if graph_path.exists():
        db = GraphDB(str(graph_path))
        for src, rel, dst in db.list_relations():
            if rel == "superseded_by" or (rel == "related_to" and src > dst):
                continue
            links.append({"source": src, "target": dst, "relation": rel})
        db.close()

    return {
        "nodes": nodes,
        "links": links,
        "tags": sorted(tag_set),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision Knowledge Graph</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #060e20;
    color: #dee5ff;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
  }

  /* Animated background canvas */
  #bg-canvas {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
  }

  #graph-container {
    position: absolute;
    inset: 0;
    z-index: 1;
  }

  svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .node-glow { filter: url(#glow); }

  .link { stroke-opacity: 0.25; stroke-width: 1; }
  .link:hover { stroke-opacity: 0.8; stroke-width: 2; }
  .link-label { font-size: 9px; fill: rgba(58,223,250,0.5); pointer-events: none; opacity: 0; }

  .node-circle { cursor: grab; transition: r 0.2s ease; }
  .node-circle:hover { filter: brightness(1.4); }
  .node-label {
    font-size: 11px;
    fill: #dee5ff;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
    text-shadow: 0 0 8px #060e20, 0 0 16px #060e20, 0 0 4px #060e20;
  }
  .node-label.highlighted { fill: #fff; font-weight: 600; }

  /* ── Glass card base ── */
  .glass-dark {
    position: relative;
    border-radius: 1rem;
    background: rgba(15,25,48,0.05);
    backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(3px);
    border: 1px solid rgba(255,255,255,0.25);
    box-shadow:
      inset 0 1px 2px 0 rgba(255,255,255,0.25),
      inset 1px 0 2px 0 rgba(255,255,255,0.15),
      inset 0 -1px 2px 0 rgba(0,0,0,0.35),
      inset -1px 0 2px 0 rgba(0,0,0,0.25),
      0 0 20px rgba(255,255,255,0.04),
      0 4px 6px -1px rgba(0,0,0,0.3),
      0 8px 20px -2px rgba(0,0,0,0.1),
      0 0 40px rgba(0,0,0,0.3);
  }
  .glass-dark::before {
    content: '';
    position: absolute; inset: 0;
    border-radius: inherit;
    pointer-events: none; z-index: 0;
    mask-image: linear-gradient(to right, black 0%, transparent 8%, transparent 92%, black 100%),
                linear-gradient(to bottom, black 0%, transparent 8%, transparent 92%, black 100%);
    mask-composite: add;
    -webkit-mask-image: linear-gradient(to right, black 0%, transparent 8%, transparent 92%, black 100%),
                        linear-gradient(to bottom, black 0%, transparent 8%, transparent 92%, black 100%);
    -webkit-mask-composite: source-over;
    backdrop-filter: blur(10px) brightness(1.8);
    -webkit-backdrop-filter: blur(10px) brightness(1.8);
  }
  .glass-dark::after {
    content: '';
    position: absolute; inset: 0;
    border-radius: inherit;
    pointer-events: none; z-index: 1;
    background:
      linear-gradient(135deg,
        rgba(255,255,255,0.02) 1%, rgba(255,255,255,0.06) 8%,
        transparent 35%, transparent 88%, rgba(255,255,255,0.05) 100%),
      linear-gradient(to right, rgba(255,255,255,0.08) 0%, transparent 2%, transparent 97%, rgba(255,255,255,0.05) 100%),
      linear-gradient(to bottom, rgba(255,255,255,0.08) 0%, transparent 2%, transparent 97%, rgba(255,255,255,0.03) 100%);
  }
  .glass-dark > * { position: relative; z-index: 2; }

  /* ── Info panel ── */
  #info-panel {
    position: fixed;
    top: 16px;
    right: 16px;
    width: 340px;
    max-height: calc(100vh - 32px);
    padding: 24px;
    overflow-y: auto;
    display: none;
    z-index: 10;
  }
  #info-panel.visible { display: block; }
  #info-panel h2 {
    font-size: 15px;
    color: #dee5ff;
    margin-bottom: 4px;
    font-weight: 700;
  }
  #info-panel .adr-id {
    font-size: 11px;
    color: #3adffa;
    margin-bottom: 12px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }
  #info-panel .meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  #info-panel .meta-label { color: rgba(222,229,255,0.4); }
  #info-panel .meta-value { color: #dee5ff; font-weight: 500; }
  #info-panel .tag {
    display: inline-block;
    background: rgba(58,223,250,0.08);
    color: #9bffce;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin: 2px 3px 2px 0;
  }
  #info-panel .tags-row { margin-top: 10px; }
  #info-panel .connections { margin-top: 14px; font-size: 12px; }
  #info-panel .connections h3 {
    font-size: 10px;
    color: #3adffa;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
  }
  #info-panel .conn-item { padding: 3px 0; color: #dee5ff; cursor: pointer; }
  #info-panel .conn-item:hover { color: #3adffa; text-decoration: underline; }
  #info-panel .conn-rel { color: rgba(222,229,255,0.4); font-size: 10px; margin-right: 6px; }
  #info-panel .close-btn {
    position: absolute; top: 16px; right: 18px;
    background: none; border: none;
    color: rgba(222,229,255,0.4); font-size: 18px;
    cursor: pointer; line-height: 1; z-index: 3;
  }
  #info-panel .close-btn:hover { color: #3adffa; }

  .status-badge {
    display: inline-block; font-size: 10px;
    padding: 2px 8px; border-radius: 8px;
    font-weight: 600; letter-spacing: 0.3px;
  }
  .status-accepted { background: rgba(155,255,206,0.12); color: #9bffce; }
  .status-proposed { background: rgba(58,223,250,0.12); color: #3adffa; }
  .status-superseded { background: rgba(200,120,80,0.12); color: #c87850; }
  .status-deprecated { background: rgba(150,150,150,0.12); color: #999; }

  /* ── Legend ── */
  #legend {
    position: fixed;
    bottom: 16px;
    left: 16px;
    padding: 14px 18px;
    z-index: 10;
    font-size: 11px;
  }
  #legend h4 {
    font-size: 10px;
    color: #3adffa;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    margin-bottom: 8px;
    font-weight: 700;
  }
  .legend-item {
    display: flex; align-items: center;
    gap: 8px; padding: 2px 0;
    color: rgba(222,229,255,0.6);
  }
  .legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .legend-line { width: 20px; height: 2px; flex-shrink: 0; border-radius: 1px; }

  /* ── Title ── */
  #title {
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 10;
    font-size: 13px;
    color: rgba(222,229,255,0.5);
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  #title span { color: #3adffa; }
  #node-count {
    font-size: 11px;
    color: rgba(155,255,206,0.4);
    margin-top: 4px;
  }
</style>
</head>
<body>

<canvas id="bg-canvas"></canvas>

<div id="title">
  <span>&#9670;</span> Decision Knowledge Graph
  <div id="node-count"></div>
</div>

<div id="graph-container">
  <svg id="graph-svg">
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
      <marker id="arrow-supersedes" viewBox="0 0 10 6" refX="10" refY="3"
              markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,3 L0,6" fill="#c87850" opacity="0.5"/>
      </marker>
      <marker id="arrow-informs" viewBox="0 0 10 6" refX="10" refY="3"
              markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,3 L0,6" fill="#3adffa" opacity="0.5"/>
      </marker>
      <marker id="arrow-refines" viewBox="0 0 10 6" refX="10" refY="3"
              markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,3 L0,6" fill="#c180ff" opacity="0.5"/>
      </marker>
    </defs>
  </svg>
</div>

<div id="info-panel" class="glass-dark">
  <button class="close-btn" onclick="closePanel()">&times;</button>
  <div id="panel-content"></div>
</div>

<div id="legend" class="glass-dark">
  <h4>Relations</h4>
  <div class="legend-item"><div class="legend-line" style="background:#c87850"></div> supersedes</div>
  <div class="legend-item"><div class="legend-line" style="background:#3adffa"></div> informs</div>
  <div class="legend-item"><div class="legend-line" style="background:#9bffce"></div> related_to</div>
  <div class="legend-item"><div class="legend-line" style="background:#c180ff"></div> refines</div>
  <div class="legend-item"><div class="legend-line" style="background:#e05555"></div> contradicts</div>
</div>

<!-- Animated background -->
<script>
(function(){
  const cv = document.getElementById('bg-canvas');
  const cx = cv.getContext('2d');
  let W, H;

  const COLORS = [{r:58,g:223,b:250},{r:193,g:128,b:255},{r:155,g:255,b:206}];

  const orbs = [];
  for(let i=0;i<4;i++){
    orbs.push({
      x:Math.random(), y:Math.random(),
      vx:(Math.random()-0.5)*0.0003, vy:(Math.random()-0.5)*0.0003,
      rad:0.18+Math.random()*0.2,
      col:COLORS[i%COLORS.length],
      opacity:0.07+Math.random()*0.05,
    });
  }

  function resize(){
    const dpr=window.devicePixelRatio||1;
    W=window.innerWidth; H=window.innerHeight;
    cv.width=W*dpr; cv.height=H*dpr;
    cv.style.width=W+'px'; cv.style.height=H+'px';
    cx.setTransform(dpr,0,0,dpr,0,0);
  }
  resize();
  window.addEventListener('resize',resize);

  function frame(){
    cx.clearRect(0,0,W,H);
    orbs.forEach(o=>{
      o.x+=o.vx; o.y+=o.vy;
      if(o.x<-0.2||o.x>1.2) o.vx*=-1;
      if(o.y<-0.2||o.y>1.2) o.vy*=-1;
      const r=o.rad*Math.max(W,H);
      const g=cx.createRadialGradient(o.x*W,o.y*H,0,o.x*W,o.y*H,r);
      g.addColorStop(0,`rgba(${o.col.r},${o.col.g},${o.col.b},${o.opacity})`);
      g.addColorStop(1,`rgba(${o.col.r},${o.col.g},${o.col.b},0)`);
      cx.fillStyle=g;
      cx.fillRect(o.x*W-r,o.y*H-r,r*2,r*2);
    });
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
</script>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const DATA = __GRAPH_DATA__;

const RELATION_COLORS = {
  supersedes: '#c87850',
  related_to: '#9bffce',
  informs: '#3adffa',
  contradicts: '#e05555',
  refines: '#c180ff',
};

const STATUS_COLORS = {
  accepted: '#9bffce',
  proposed: '#3adffa',
  superseded: '#c87850',
  deprecated: '#666',
};

const TAG_PALETTE = [
  '#3adffa', '#c180ff', '#9bffce', '#ffa94d', '#ff7ab8',
  '#4dc9f6', '#a78bfa', '#50c878', '#f67019', '#acc236',
];

const tagColorMap = {};
DATA.tags.forEach((tag, i) => {
  tagColorMap[tag] = TAG_PALETTE[i % TAG_PALETTE.length];
});

function primaryTagColor(node) {
  if (node.tags && node.tags.length > 0) {
    return tagColorMap[node.tags[0]] || '#7a7aff';
  }
  return '#7a7aff';
}

// Connection count for node sizing
const connectionCount = {};
DATA.nodes.forEach(n => connectionCount[n.id] = 0);
DATA.links.forEach(l => {
  const src = typeof l.source === 'object' ? l.source.id : l.source;
  const dst = typeof l.target === 'object' ? l.target.id : l.target;
  connectionCount[src] = (connectionCount[src] || 0) + 1;
  connectionCount[dst] = (connectionCount[dst] || 0) + 1;
});

document.getElementById('node-count').textContent =
  DATA.nodes.length + ' decisions · ' + DATA.links.length + ' connections';

const svg = d3.select('#graph-svg');
const container = svg.append('g');

// Zoom
const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on('zoom', (event) => container.attr('transform', event.transform));
svg.call(zoom);

const width = window.innerWidth;
const height = window.innerHeight;

// Center initially
svg.call(zoom.transform, d3.zoomIdentity.translate(width/2, height/2));

// Tag clustering: nudge same-tag nodes toward shared centroid (gentle, inside sphere)
function tagCluster(alpha) {
  const centroids = {};
  const counts = {};
  DATA.nodes.forEach(d => {
    const tag = (d.tags && d.tags[0]) || '__none__';
    if (!centroids[tag]) { centroids[tag] = {x: 0, y: 0}; counts[tag] = 0; }
    centroids[tag].x += d.x || 0;
    centroids[tag].y += d.y || 0;
    counts[tag]++;
  });
  for (const tag in centroids) {
    centroids[tag].x /= counts[tag];
    centroids[tag].y /= counts[tag];
  }
  const strength = 0.02 * alpha;
  DATA.nodes.forEach(d => {
    const tag = (d.tags && d.tags[0]) || '__none__';
    const c = centroids[tag];
    d.vx += (c.x - d.x) * strength;
    d.vy += (c.y - d.y) * strength;
  });
}

// Force simulation — scales with node count
const nodeCount = DATA.nodes.length;
const baseRadius = Math.max(80, Math.sqrt(nodeCount) * 18);
const chargeStr = nodeCount > 500 ? -40 : nodeCount > 100 ? -100 : -200;
const linkDist = nodeCount > 500 ? 25 : nodeCount > 100 ? 45 : 80;

const simulation = d3.forceSimulation(DATA.nodes)
  .force('link', d3.forceLink(DATA.links).id(d => d.id).distance(linkDist).strength(0.4))
  .force('charge', d3.forceManyBody().strength(chargeStr).distanceMax(baseRadius * 1.5))
  .force('center', d3.forceCenter(0, 0).strength(0.1))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 2).strength(0.6))
  .force('tagCluster', tagCluster)
  .alphaDecay(0.025)
  .velocityDecay(0.4);

function nodeRadius(d) {
  const count = connectionCount[d.id] || 0;
  return Math.min(2 + count * 0.3, 6);
}

// Links
const linkGroup = container.append('g');
const link = linkGroup.selectAll('line')
  .data(DATA.links)
  .join('line')
  .attr('class', 'link')
  .attr('stroke', d => RELATION_COLORS[d.relation] || '#444')
  .attr('marker-end', d => {
    if (d.relation === 'supersedes') return 'url(#arrow-supersedes)';
    if (d.relation === 'informs') return 'url(#arrow-informs)';
    if (d.relation === 'refines') return 'url(#arrow-refines)';
    return null;
  });

// Link labels (hidden until hover)
const linkLabels = linkGroup.selectAll('text')
  .data(DATA.links)
  .join('text')
  .attr('class', 'link-label')
  .text(d => d.relation);

// Node groups
const nodeGroup = container.append('g');
const node = nodeGroup.selectAll('g')
  .data(DATA.nodes)
  .join('g')
  .attr('class', 'node-group');

// Glow circle (behind main circle)
node.append('circle')
  .attr('r', d => nodeRadius(d) + 4)
  .attr('fill', d => primaryTagColor(d))
  .attr('opacity', 0.15)
  .attr('class', 'node-glow');

// Main circle
node.append('circle')
  .attr('r', d => nodeRadius(d))
  .attr('fill', d => primaryTagColor(d))
  .attr('opacity', 0.85)
  .attr('class', 'node-circle')
  .attr('stroke', d => primaryTagColor(d))
  .attr('stroke-width', 1.5)
  .attr('stroke-opacity', 0.4);

// Labels — hidden by default, shown on hover
node.append('text')
  .attr('class', 'node-label')
  .attr('dy', d => nodeRadius(d) + 10)
  .attr('opacity', 0)
  .text(d => d.id);

// Drag behavior
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

// Click to show info
node.on('click', (event, d) => {
  event.stopPropagation();
  showPanel(d);
  highlightNode(d);
});

svg.on('click', () => {
  closePanel();
  clearHighlight();
});

// Hover effects
node.on('mouseenter', (event, d) => {
  highlightNode(d);
  // Show connected link labels
  linkLabels.attr('opacity', l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 0.8 : 0;
  });
}).on('mouseleave', () => {
  if (!document.getElementById('info-panel').classList.contains('visible')) {
    clearHighlight();
  }
  linkLabels.attr('opacity', 0);
});

function highlightNode(d) {
  const connected = new Set();
  DATA.links.forEach(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === d.id) connected.add(tid);
    if (tid === d.id) connected.add(sid);
  });
  connected.add(d.id);

  node.select('.node-circle')
    .attr('opacity', n => connected.has(n.id) ? 1 : 0.15);
  node.select('.node-glow')
    .attr('opacity', n => connected.has(n.id) ? 0.25 : 0.03);
  node.select('.node-label')
    .attr('opacity', n => connected.has(n.id) ? 0.9 : 0)
    .attr('fill', n => connected.has(n.id) ? '#dee5ff' : '#1a2030')
    .classed('highlighted', n => n.id === d.id);

  link.attr('stroke-opacity', l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 0.7 : 0.05;
  }).attr('stroke-width', l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === d.id || tid === d.id) ? 2 : 1;
  });
}

function clearHighlight() {
  node.select('.node-circle').attr('opacity', 0.85);
  node.select('.node-glow').attr('opacity', 0.15);
  node.select('.node-label').attr('opacity', 0).attr('fill', '#dee5ff').classed('highlighted', false);
  link.attr('stroke-opacity', 0.25).attr('stroke-width', 1);
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

  const statusClass = 'status-' + (d.status || 'proposed');
  let html = `
    <div class="adr-id">${d.id}</div>
    <h2>${d.title}</h2>
    <div style="margin: 8px 0">
      <span class="status-badge ${statusClass}">${d.status}</span>
    </div>
    <div class="meta-row"><span class="meta-label">Date</span><span class="meta-value">${d.date}</span></div>
    <div class="meta-row"><span class="meta-label">Project</span><span class="meta-value">${d.project}</span></div>
    <div class="tags-row">${(d.tags||[]).map(t =>
      '<span class="tag" style="border-left:2px solid '+( tagColorMap[t]||'#7a7aff' )+'">'+t+'</span>'
    ).join('')}</div>
  `;

  if (connected.length > 0) {
    html += '<div class="connections"><h3>Connections</h3>';
    connected.forEach(c => {
      const relColor = RELATION_COLORS[c.relation] || '#666';
      const arrow = c.dir === 'out' ? '&rarr;' : '&larr;';
      html += `<div class="conn-item" onclick="focusNode('${c.id}')">
        <span class="conn-rel" style="color:${relColor}">${c.relation} ${arrow}</span> ${c.id}
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

// Tick
simulation.on('tick', () => {
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  linkLabels
    .attr('x', d => (d.source.x + d.target.x) / 2)
    .attr('y', d => (d.source.y + d.target.y) / 2);

  node.attr('transform', d => `translate(${d.x},${d.y})`);
});

// Resize
window.addEventListener('resize', () => {
  simulation.force('center', d3.forceCenter(0, 0));
  simulation.alpha(0.1).restart();
});
</script>
</body>
</html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Visualize the decision knowledge graph")
    parser.add_argument("-o", "--output", default=str(DECISIONS_DIR / "graph.html"))
    parser.add_argument("--open", action="store_true", help="Open in browser after generating")
    args = parser.parse_args()

    data = collect_graph_data()
    html = HTML_TEMPLATE.replace("__GRAPH_DATA__", json.dumps(data, indent=2))

    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(json.dumps({"output": str(output_path), "nodes": len(data["nodes"]), "links": len(data["links"])}))

    if args.open:
        webbrowser.open(f"file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
