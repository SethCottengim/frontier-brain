# frontier-brain v2 — Cross-Project Decision Memory

Personal engineering decision memory that persists across projects and years. Decisions auto-captured from any Claude Code session, stored centrally, queryable via graph + full-text search, visualized as interactive knowledge graph.

## How to Execute

Read this file. Find the first task with status `[ ]` whose dependencies are all `[x]`. Complete it. Mark it `[x]`. Stop.

## Design Decisions

| # | Question | Resolution |
|---|----------|------------|
| 1 | Hook scope | Global — registered in `~/.claude/settings.json`, fires every prompt |
| 2 | Storage location | `~/.claude/decisions/` — central, survives project clones/deletes |
| 3 | Project identification | Git remote URL (primary) + directory basename (fallback) |
| 4 | ID scheme | Global sequential integers, project tracked in metadata |
| 5 | Record types | `decision`, `knowledge`, `context` |
| 6 | Schema | 10 fields + free-text body; `affects` optional |
| 7 | Relationships | `supersedes` (directional, auto-inverse) + `related` (bidirectional) only |
| 8 | Quality gate | Claude judges entirely — no regex pre-filter |
| 9 | Injection | Every prompt; dual-purpose (record evaluation + recall nudge) |
| 10 | Confirmation | One-line after recording: "Recorded #N: title" |
| 11 | Engine location | `~/.claude/frontier-brain/bin/` — installed, not run from repo |
| 12 | Migration | Drop old 8 ADRs, clean start at ID 1 |
| 13 | Visualization | Color=project, shape=type, filter sidebar, legend panel |
| 14 | Recall | Manual (`/recall`) + Claude nudges at key moments, user decides |
| 15 | Database | Single SQLite `brain.db` — FTS5 + relational tables in one file |

## Schema

```yaml
---
id: 42
title: Strands SDK over LangChain for agent framework
type: decision          # decision | knowledge | context
status: active          # active | superseded | deprecated
date: 2026-04-28
project: sempl-core/agents
tags: [agent-framework, architecture]
affects: [agents/apps/bma_agent/]   # optional, default []
recorded_by: e427923
supersedes: []
related: [3]
---
Free-text body. 2-5 sentences. No mandatory sections.
Captures what was chosen and why.
```

Filename format: `NNN-slug.md` (zero-padded 3 digits)

## Installed Layout

```
~/.claude/
├── decisions/              # all records (markdown source of truth)
│   ├── 001-sempl-context.md
│   ├── 002-strands-over-langchain.md
│   ├── brain.db            # single SQLite: FTS5 + relational
│   └── graph.html          # generated visualization
├── frontier-brain/         # tooling (installed from repo)
│   ├── bin/
│   │   ├── decision-engine.py
│   │   └── visualize.py
│   └── lib/
│       ├── graphdb.py
│       └── router.py
├── hooks/
│   └── frontier-brain/
│       └── decision-detect.js
└── settings.json           # global hook registration
```

## How It Works

```
Any Claude Code session (any project, any directory)
  → UserPromptSubmit hook fires (every prompt)
  → Injects dual-purpose instruction:
      1. Evaluate: significant engineering decision? Record it.
      2. Evaluate: user choosing between alternatives? Offer to recall.
  → Claude judges significance (no regex gate)
  → If recording: writes markdown → indexes brain.db → confirms one line
  → If nudging: "You may have past decisions on this. Want me to check?"
  → User controls recall — never auto-queried
```

## Record Types

| Type | What | Example |
|------|------|---------|
| `context` | Project purpose, goals, constraints | "SEMPL automates ISO 15288 via staged agent pipelines" |
| `decision` | Choice between alternatives + rationale | "Strands over LangChain — lighter, native Bedrock" |
| `knowledge` | Validated fact learned through experience | "Unset VPC endpoint env var locally or Bedrock calls fail" |

## Visualization

- Dark theme, Obsidian-style force-directed graph
- **Color** = project (auto-assigned palette + legend)
- **Shape** = type (circle=decision, diamond=knowledge, hexagon=context)
- **Filter sidebar** — toggle projects and types on/off
- **Legend panel** — always visible, shows color→project + shape→type

---

## Tasks

Each task scoped to <150k context tokens. Dependencies listed — only start a task when all deps are `[x]`.

### Phase 1 — Foundation

- [x] **T1: Create directory structure + new schema** | deps: none
  - Create directories: `~/.claude/decisions/`, `~/.claude/frontier-brain/bin/`, `~/.claude/frontier-brain/lib/`, `~/.claude/hooks/frontier-brain/`
  - Write `decisions/SCHEMA.md` in this repo reflecting the new schema (see Schema section above)
  - Write `decisions/TEMPLATE.md` with blank template matching new schema
  - New schema: 10 fields (id, title, type, status, date, project, tags, affects, recorded_by, supersedes, related) + free-text body
  - Two relationship types: `supersedes` (directional, auto-inverse) and `related` (bidirectional)
  - Filename format: `NNN-slug.md` (zero-padded 3 digits, no ADR- prefix)

- [x] **T2: Rewrite decision-detect.js — simplified global hook** | deps: none
  - Rewrite `hooks/decision-detect.js` as minimal global hook. No regex detection — Claude judges everything.
  - Hook reads user prompt from stdin (hook event JSON)
  - Always injects dual-purpose additionalContext:
    1. RECORD: "Evaluate if this conversation contains a significant engineering decision (architecture, stack selection, complexity tradeoff, environment config, project context/goals). If yes, record to `~/.claude/decisions/` using `python3 ~/.claude/frontier-brain/bin/decision-engine.py`. Test: would forgetting this hurt in 3 months? If trivial, skip silently. Confirm with one line: 'Recorded #N: title'"
    2. RECALL NUDGE: "If the user is evaluating alternatives or making an engineering choice, offer to search past decisions before proceeding."
  - Derive project from CWD: try `git remote get-url origin` → extract repo name, fallback to directory basename
  - Pass project name + recorded_by ($USER) in injected context
  - Remove: all COMMITMENT_VERBS, ARCHITECTURE_NOUNS, FALSE_POSITIVE_FILTERS regex arrays
  - Target install location: `~/.claude/hooks/frontier-brain/decision-detect.js`
  - Should be ~20-30 lines total

### Phase 2 — Core libs

- [x] **T3: Rewrite graphdb.py for single-db architecture** | deps: T1
  - Update `lib/graphdb.py` to work within a single SQLite database (brain.db) instead of its own separate file
  - GraphDB class accepts a sqlite3 connection (or db path) rather than managing its own file
  - Keep only `supersedes`/`superseded_by` and `related_to` relationship types
  - Remove `informs`, `informed_by`, `contradicts`, `refines`, `refined_by`
  - Tables coexist alongside FTS5 virtual table in brain.db

- [x] **T4: Clean up old ADRs + update project docs** | deps: T1
  - Delete all 8 existing ADR files: `decisions/ADR-001*.md` through `decisions/ADR-008*.md`
  - Delete old `decisions/graph.db`, `decisions/search.db`, `decisions/graph.html` if present
  - Update `CLAUDE.md` to reflect new architecture: central store in `~/.claude/decisions/`, global hook, three types, single brain.db, new viz features
  - Update skills in `.claude/skills/` (decision-record, decision-recall) to reference new paths (`~/.claude/frontier-brain/bin/decision-engine.py`, `~/.claude/decisions/`)

### Phase 3a — Engine core

- [x] **T5: Engine — core parser + single-db schema + index command** | deps: T1, T3
  - Rewrite `bin/decision-engine.py` — first half: core infrastructure
  - New frontmatter parser for updated schema (integer IDs, type field, affects, recorded_by)
  - Single SQLite db setup — `brain.db` at `~/.claude/decisions/brain.db` with:
    - `decisions` table (id, title, type, status, date, project, tags_json, affects_json, recorded_by, body, file)
    - `decisions_fts` FTS5 virtual table (id, title, tags, body, project)
    - `relationships` table (source_id, target_id, relation_type)
  - `discover_records()` — glob `~/.claude/decisions/*.md`
  - `index` command — rebuild brain.db from markdown files. Parse frontmatter, populate decisions table + FTS5, extract relationships from supersedes/related fields
  - `next-id` command — max(id) + 1 from brain.db, or 1 if empty
  - Constants: `DECISIONS_DIR = Path.home() / ".claude" / "decisions"`, `DB_PATH = DECISIONS_DIR / "brain.db"`
  - Do NOT implement search, graph, related, or serve commands yet

### Phase 3b — Engine queries + Viz core (parallel)

- [x] **T6: Engine — search + graph + related commands** | deps: T5
  - Add query commands to decision-engine.py built in T5
  - `search <query>` — FTS5 search on decisions_fts. Optional flags: `--project <name>`, `--type <type>`. Returns ranked JSON.
  - `graph <id>` — traverse relationships table. Return all connected records + metadata as JSON.
  - `related <id>` — combined: graph neighbors + records sharing same tags. Deduplicated JSON.
  - `detect_project()` helper — try `git remote get-url origin` → extract repo name, fallback to basename of CWD. Used by hook injection.
  - Do NOT implement `serve` command

- [x] **T7: Viz — data layer + HTML scaffold + force graph rendering** | deps: T5
  - Rewrite `bin/visualize.py` — first half: core rendering
  - Read from `~/.claude/decisions/brain.db` — query all records + relationships
  - Generate nodes JSON (id, title, type, project, tags) and links JSON (source, target, relation_type)
  - HTML scaffold: dark theme (#0d1117 background), full-viewport canvas
  - Force-directed graph using d3-force (inline/vendored, no CDN)
  - Shape by type: circle=decision, diamond=knowledge, hexagon=context
  - Color by project: auto-assign from palette based on unique project values
  - Node labels (title), hover tooltip (full metadata)
  - Zoom/pan, drag nodes, Obsidian-style glow aesthetic (text-shadow, drop-shadow on nodes)
  - Output to `~/.claude/decisions/graph.html`, `--open` flag opens in browser
  - Do NOT implement filter sidebar or legend panel yet

### Phase 4 — Viz controls

- [x] **T8: Viz — legend panel + filter sidebar + polish** | deps: T7
  - Add UI controls to visualize.py graph from T7
  - Legend panel (top-right): project → color dots, type → shape icons. Always visible, semi-transparent bg.
  - Filter sidebar (left): collapsible, checkboxes per project + per type, "All/None" toggles. Filtering hides nodes + connected edges, re-runs force layout.
  - Edge styling: solid lines for `related`, dashed for `supersedes`
  - Node count display ("showing X of Y")
  - Smooth transitions on filter toggle
  - Keep existing aesthetics: dark theme, glow, force physics, interactive

### Phase 5 — Distribution

- [x] **T9: Create install.sh** | deps: T2, T6, T8
  - Create `install.sh` in frontier-brain repo root
  - Creates directories: `~/.claude/decisions/`, `~/.claude/frontier-brain/bin/`, `~/.claude/frontier-brain/lib/`, `~/.claude/hooks/frontier-brain/`
  - Copies files from repo to install locations:
    - `bin/decision-engine.py` → `~/.claude/frontier-brain/bin/`
    - `bin/visualize.py` → `~/.claude/frontier-brain/bin/`
    - `lib/graphdb.py` → `~/.claude/frontier-brain/lib/`
    - `lib/router.py` → `~/.claude/frontier-brain/lib/` (if still needed)
    - `hooks/decision-detect.js` → `~/.claude/hooks/frontier-brain/`
  - Registers global hook in `~/.claude/settings.json`: adds `UserPromptSubmit` entry pointing to installed hook. Merges into existing hooks (don't clobber PreToolUse/PostToolUse).
  - Initializes empty brain.db via `decision-engine.py index`
  - Prints confirmation with NTID ($USER) and installed paths

### Phase 6 — Verification

- [x] **T10: End-to-end test** | deps: T9, T4
  - Run `install.sh` — verify dirs created, files copied, hook registered
  - Verify `~/.claude/settings.json` has UserPromptSubmit hook without clobbering existing hooks
  - Run `decision-engine.py next-id` — should return 1
  - Manually create a test context record for a project
  - Run `decision-engine.py index` — verify brain.db populated
  - Run `decision-engine.py search "<project>"` — verify FTS5 returns result
  - Create a second record (type: decision) related to first
  - Run `decision-engine.py graph 1` — verify relationship traversal
  - Run `visualize.py --open` — verify graph shows nodes with correct colors/shapes, legend, filters
  - Verify hook injection format by inspecting decision-detect.js output
