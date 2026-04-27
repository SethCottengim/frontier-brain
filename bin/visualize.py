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
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #0a0a0f;
    color: #c4c4cc;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
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

  /* Glow filter for nodes */
  .node-glow {
    filter: url(#glow);
  }

  /* Links */
  .link {
    stroke-opacity: 0.25;
    stroke-width: 1;
  }
  .link:hover {
    stroke-opacity: 0.8;
    stroke-width: 2;
  }
  .link-label {
    font-size: 9px;
    fill: #666;
    pointer-events: none;
    opacity: 0;
  }

  /* Nodes */
  .node-circle {
    cursor: grab;
    transition: r 0.2s ease;
  }
  .node-circle:hover {
    filter: brightness(1.4);
  }
  .node-label {
    font-size: 11px;
    fill: #aaa;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
    text-shadow: 0 0 8px #0a0a0f, 0 0 16px #0a0a0f, 0 0 4px #0a0a0f;
  }
  .node-label.highlighted {
    fill: #eee;
    font-weight: 600;
  }

  /* Panel */
  #info-panel {
    position: fixed;
    top: 16px;
    right: 16px;
    width: 320px;
    max-height: calc(100vh - 32px);
    background: rgba(18, 18, 28, 0.92);
    border: 1px solid rgba(100, 100, 140, 0.2);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(20px);
    overflow-y: auto;
    display: none;
    z-index: 10;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  #info-panel.visible { display: block; }
  #info-panel h2 {
    font-size: 15px;
    color: #e0e0f0;
    margin-bottom: 4px;
    font-weight: 600;
  }
  #info-panel .adr-id {
    font-size: 11px;
    color: #7a7aff;
    margin-bottom: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  #info-panel .meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 4px 0;
    border-bottom: 1px solid rgba(100,100,140,0.1);
  }
  #info-panel .meta-label { color: #666; }
  #info-panel .meta-value { color: #aaa; }
  #info-panel .tag {
    display: inline-block;
    background: rgba(120, 120, 255, 0.12);
    color: #9999ff;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin: 2px 3px 2px 0;
  }
  #info-panel .tags-row { margin-top: 10px; }
  #info-panel .connections {
    margin-top: 14px;
    font-size: 12px;
  }
  #info-panel .connections h3 {
    font-size: 12px;
    color: #888;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 500;
  }
  #info-panel .conn-item {
    padding: 3px 0;
    color: #aaa;
    cursor: pointer;
  }
  #info-panel .conn-item:hover { color: #bbb; text-decoration: underline; }
  #info-panel .conn-rel {
    color: #666;
    font-size: 10px;
    margin-right: 6px;
  }
  #info-panel .close-btn {
    position: absolute;
    top: 12px;
    right: 14px;
    background: none;
    border: none;
    color: #666;
    font-size: 18px;
    cursor: pointer;
    line-height: 1;
  }
  #info-panel .close-btn:hover { color: #aaa; }

  .status-badge {
    display: inline-block;
    font-size: 10px;
    padding: 1px 7px;
    border-radius: 8px;
    font-weight: 500;
    letter-spacing: 0.3px;
  }
  .status-accepted { background: rgba(80,200,120,0.15); color: #50c878; }
  .status-proposed { background: rgba(100,140,255,0.15); color: #648cff; }
  .status-superseded { background: rgba(200,120,80,0.15); color: #c87850; }
  .status-deprecated { background: rgba(150,150,150,0.15); color: #999; }

  /* Legend */
  #legend {
    position: fixed;
    bottom: 16px;
    left: 16px;
    background: rgba(18, 18, 28, 0.85);
    border: 1px solid rgba(100, 100, 140, 0.15);
    border-radius: 10px;
    padding: 12px 16px;
    backdrop-filter: blur(12px);
    z-index: 10;
    font-size: 11px;
  }
  #legend h4 {
    font-size: 10px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    font-weight: 500;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 2px 0;
    color: #888;
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .legend-line {
    width: 20px;
    height: 2px;
    flex-shrink: 0;
    border-radius: 1px;
  }

  /* Title */
  #title {
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 10;
    font-size: 13px;
    color: #555;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  #title span { color: #7a7aff; }
  #node-count {
    font-size: 11px;
    color: #444;
    margin-top: 4px;
  }
</style>
</head>
<body>

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
        <path d="M0,0 L10,3 L0,6" fill="#648cff" opacity="0.5"/>
      </marker>
      <marker id="arrow-refines" viewBox="0 0 10 6" refX="10" refY="3"
              markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,3 L0,6" fill="#a78bfa" opacity="0.5"/>
      </marker>
    </defs>
  </svg>
</div>

<div id="info-panel">
  <button class="close-btn" onclick="closePanel()">&times;</button>
  <div id="panel-content"></div>
</div>

<div id="legend">
  <h4>Relations</h4>
  <div class="legend-item"><div class="legend-line" style="background:#c87850"></div> supersedes</div>
  <div class="legend-item"><div class="legend-line" style="background:#648cff"></div> informs</div>
  <div class="legend-item"><div class="legend-line" style="background:#50c878"></div> related_to</div>
  <div class="legend-item"><div class="legend-line" style="background:#a78bfa"></div> refines</div>
  <div class="legend-item"><div class="legend-line" style="background:#e05555"></div> contradicts</div>
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const DATA = __GRAPH_DATA__;

const RELATION_COLORS = {
  supersedes: '#c87850',
  related_to: '#50c878',
  informs: '#648cff',
  contradicts: '#e05555',
  refines: '#a78bfa',
};

const STATUS_COLORS = {
  accepted: '#50c878',
  proposed: '#648cff',
  superseded: '#c87850',
  deprecated: '#666',
};

// Tag-based color palette for node coloring
const TAG_PALETTE = [
  '#7a7aff', '#ff7ab8', '#50c878', '#ffa94d', '#a78bfa',
  '#4dc9f6', '#f67019', '#f53794', '#acc236', '#166a8f',
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
  const strength = 0.06 * alpha;
  DATA.nodes.forEach(d => {
    const tag = (d.tags && d.tags[0]) || '__none__';
    const c = centroids[tag];
    d.vx += (c.x - d.x) * strength;
    d.vy += (c.y - d.y) * strength;
  });
}

// Force simulation — tight sphere + tag clustering
const nodeCount = DATA.nodes.length;
const baseRadius = Math.max(80, Math.sqrt(nodeCount) * 22);

const simulation = d3.forceSimulation(DATA.nodes)
  .force('link', d3.forceLink(DATA.links).id(d => d.id).distance(45).strength(0.9))
  .force('charge', d3.forceManyBody().strength(-80).distanceMax(baseRadius * 2))
  .force('center', d3.forceCenter(0, 0).strength(0.3))
  .force('radial', d3.forceRadial(baseRadius * 0.6, 0, 0).strength(0.15))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 3).strength(0.7))
  .force('tagCluster', tagCluster)
  .alphaDecay(0.008)
  .velocityDecay(0.4);

function nodeRadius(d) {
  const count = connectionCount[d.id] || 0;
  return 2.5 + count * 1;
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
    .attr('fill', n => connected.has(n.id) ? '#ddd' : '#333')
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
  node.select('.node-label').attr('opacity', 0).attr('fill', '#aaa').classed('highlighted', false);
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
