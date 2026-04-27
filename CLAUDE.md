# frontier-brain — Decision Knowledge Graph

Autonomous decision memory for Claude Code. Decisions made during sessions are auto-captured as ADRs, dual-indexed in a relationship graph (SQLite) and full-text search (FTS5). Claude queries both indexes for context during reasoning.

## How It Works

```
User makes decision in conversation
  → UserPromptSubmit hook detects decision language
  → Injects instruction to auto-record
  → Claude writes ADR file (no human review)
  → Engine indexes in graph + FTS5
  → Future sessions can recall via /frontier-brain:recall
```

## Commands

| Command | What |
|---------|------|
| `python bin/decision-engine.py index` | Rebuild both databases from decisions/*.md |
| `python bin/decision-engine.py search "<query>"` | FTS5 full-text search, ranked JSON |
| `python bin/decision-engine.py graph <ADR-ID>` | Graph traversal, connected decisions JSON |
| `python bin/decision-engine.py related <ADR-ID>` | Combined: graph neighbors + tag matches |
| `python bin/decision-engine.py next-id` | Next sequential ADR ID |
| `python bin/visualize.py --open` | Generate + open interactive graph visualization |

## Skills

- **decision-recall** — Find past decisions by topic or ID. Dual-queries FTS5 + graph.
- **decision-record** — Write new ADR from conversation context. No human review.

## Slash Commands

- `/frontier-brain:recall <topic>` — Search past decisions
- `/frontier-brain:record` — Record a decision from this conversation

## ADR Format

YAML frontmatter (8 fields) + 4 body sections. See `decisions/SCHEMA.md` for full spec.

```yaml
id: ADR-XXX
title: ...
status: proposed | accepted | superseded | deprecated
date: YYYY-MM-DD
tags: []
supersedes: []
related: []
project: frontier-brain
```

## Architecture

- **Source of truth**: Markdown files in `decisions/`
- **Graph DB**: `decisions/graph.db` — relationship triples (SQLite, zero deps)
- **Search DB**: `decisions/search.db` — FTS5 full-text index
- **Both databases are derived** — delete and rebuild with `index` command
- **Engine**: `bin/decision-engine.py` — Python CLI, deps: pyyaml only
- **Hook**: `hooks/decision-detect.js` — regex-based, <100ms, no subprocess

## Dependencies

- Python 3.11+ with pyyaml
- Node.js (for hook only)
- No other external dependencies

## Key Decisions

All project decisions are recorded as ADRs in `decisions/`. Key ones:
- ADR-001: Hybrid graph + FTS5 storage
- ADR-002: Zero-dep graph library (no vendored graphdb)
- ADR-003: Autonomous recording without human review
- ADR-007: Markdown as source of truth
