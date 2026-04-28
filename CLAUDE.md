# frontier-brain — Cross-Project Decision Memory

Personal engineering decision memory that persists across projects and years. Decisions auto-captured from any Claude Code session, stored centrally in `~/.claude/decisions/`, queryable via graph + full-text search, visualized as interactive knowledge graph.

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

## Commands

| Command | What |
|---------|------|
| `python3 ~/.claude/frontier-brain/bin/decision-engine.py index` | Rebuild brain.db from `~/.claude/decisions/*.md` |
| `python3 ~/.claude/frontier-brain/bin/decision-engine.py search "<query>"` | FTS5 full-text search, ranked JSON |
| `python3 ~/.claude/frontier-brain/bin/decision-engine.py graph <id>` | Graph traversal, connected records JSON |
| `python3 ~/.claude/frontier-brain/bin/decision-engine.py related <id>` | Combined: graph neighbors + tag matches |
| `python3 ~/.claude/frontier-brain/bin/decision-engine.py next-id` | Next sequential integer ID |
| `python3 ~/.claude/frontier-brain/bin/visualize.py --open` | Generate + open interactive graph visualization |

## Skills

- **decision-recall** — Find past decisions by topic or ID. Queries FTS5 + graph in brain.db.
- **decision-record** — Write new record from conversation context. No human review.

## Slash Commands

- `/frontier-brain:recall <topic>` — Search past decisions
- `/frontier-brain:record` — Record a decision from this conversation

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
```

Filename format: `NNN-slug.md` (zero-padded 3 digits)

## Architecture

- **Source of truth**: Markdown files in `~/.claude/decisions/`
- **Database**: Single `~/.claude/decisions/brain.db` — FTS5 + relational tables in one SQLite file
- **Engine**: `~/.claude/frontier-brain/bin/decision-engine.py` — Python CLI
- **Visualization**: `~/.claude/frontier-brain/bin/visualize.py` — generates `~/.claude/decisions/graph.html`
- **Graph lib**: `~/.claude/frontier-brain/lib/graphdb.py` — relationships within brain.db
- **Hook**: `~/.claude/hooks/frontier-brain/decision-detect.js` — global, fires every prompt, Claude judges significance
- **Relationships**: `supersedes` (directional, auto-inverse) + `related` (bidirectional) only

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

## Dependencies

- Python 3.11+
- Node.js (for hook only)
- No other external dependencies

## Visualization

- Dark theme, Obsidian-style force-directed graph
- **Color** = project (auto-assigned palette + legend)
- **Shape** = type (circle=decision, diamond=knowledge, hexagon=context)
- **Filter sidebar** — toggle projects and types on/off
- **Legend panel** — always visible, shows color→project + shape→type
