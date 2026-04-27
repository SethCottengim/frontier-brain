# Decision Knowledge Graph — Implementation Plan

## Vision

Autonomous decision memory for Claude Code. Decisions made during sessions auto-captured as ADRs, stored in markdown, dual-indexed in a relationship graph (graphdb) AND full-text search (SQLite FTS5). Claude queries both indexes for context during reasoning — graph for "what relates to what", FTS5 for "find decisions about X".

No manual review. Claude detects, records, indexes. Human can edit later if needed.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Claude Code Session                     │
│                                                           │
│  ┌────────────────────┐    ┌───────────────────────────┐  │
│  │ UserPromptSubmit    │    │ Skill: decision-recall    │  │
│  │ Hook                │    │                           │  │
│  │                     │    │ Auto or /recall "auth"    │  │
│  │ Detects decision →  │    │ → FTS5 text search        │  │
│  │ Injects instruction │    │ → graphdb traversal       │  │
│  │ "auto-record this"  │    │ → merged ranked results   │  │
│  └──────────┬──────────┘    └──────────┬────────────────┘  │
│             │                          │                   │
│             ▼                          │                   │
│  ┌────────────────────┐               │                   │
│  │ Claude auto-records │               │                   │
│  │ (no human review)   │               │                   │
│  └──────────┬──────────┘               │                   │
│             │                          │                   │
│             ▼                          ▼                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  decisions/ directory                 │  │
│  │                                                      │  │
│  │  ADR-001-use-mobx-for-state.md                      │  │
│  │  ADR-002-strands-over-langchain.md                  │  │
│  │                                                      │  │
│  │  ┌──────────────┐    ┌──────────────────┐           │  │
│  │  │ graph.db     │    │ search.db        │           │  │
│  │  │ (graphdb)    │    │ (SQLite FTS5)    │           │  │
│  │  │              │    │                  │           │  │
│  │  │ Relationships│    │ Full-text search │           │  │
│  │  │ supersedes   │    │ Ranked results   │           │  │
│  │  │ related_to   │    │ Tag filtering    │           │  │
│  │  │ informs      │    │ Date ranges      │           │  │
│  │  │ contradicts  │    │                  │           │  │
│  │  └──────────────┘    └──────────────────┘           │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Hybrid Storage: graphdb + SQLite FTS5

**graphdb** (CodyKochmann/graphdb — Python SQLite triple-store):
- Stores decision relationships as triples: `(ADR-001, "supersedes", ADR-000)`
- Chainable traversal: `db["ADR-001"].related_to.supersedes.to(list)`
- Relation types: `supersedes`, `superseded_by`, `related_to`, `informs`, `contradicts`, `refines`
- Good at: "what decisions led to this one?", "what does this supersede?"

**SQLite FTS5** (stdlib, no extra deps):
- Full-text index over ADR title + body + tags
- Ranked search with BM25 scoring
- Good at: "find decisions about authentication", "what did we decide about state management?"

**Why both:** Graph answers "how are decisions connected?" FTS5 answers "find decisions about X." Neither does both well alone. Combined = complete retrieval.

**Single CLI (`bin/decision-engine.py`)** wraps both, exposes unified interface.

### 2. ADR Format: Lightweight with YAML frontmatter

```markdown
---
id: ADR-001
title: Use MobX for State Management
status: accepted
date: 2026-04-27
tags: [frontend, state-management, react]
supersedes: []
related: [ADR-003]
project: sempl-core/ui
---

## Context
[Why this decision came up]

## Considered Options
### Option A: MobX
- Pro: ...
- Con: ...

### Option B: Redux
- Pro: ...
- Con: ...

## Decision
[What we chose and why]

## Consequences
[What changes because of this]
```

### 3. Auto-Record (No Human Review)

Flow:
1. **UserPromptSubmit hook** scans prompt for decision signals
2. If detected → injects `additionalContext` instructing Claude to auto-record
3. Claude writes ADR file + updates both indexes
4. No confirmation prompt, no review step
5. Human can edit/delete ADRs later if quality is off

Decision signals (regex): "let's go with", "decided to use", "choosing X over Y", "we should use", "approved", architecture keywords + commitment verbs.

### 4. Python-Based Engine (matches user's stack)

User stack is Python-heavy (Django, Strands, uv). graphdb is Python. Going all-Python:
- `bin/decision-engine.py` — CLI wrapping graphdb + FTS5
- Dependencies: `graphdb` (local install from Downloads), `pyyaml`
- Hooks shell out to Python same as gitnexus shells out to Node

### 5. Relationship Types

| Relation | Meaning | Example |
|----------|---------|---------|
| `supersedes` | Replaces an older decision | ADR-005 supersedes ADR-001 |
| `superseded_by` | Inverse of supersedes (auto-created) | ADR-001 superseded_by ADR-005 |
| `related_to` | Topically connected | ADR-001 related_to ADR-003 |
| `informs` | Influenced but didn't replace | ADR-002 informs ADR-007 |
| `contradicts` | Tension between decisions | ADR-004 contradicts ADR-006 |
| `refines` | Narrows scope of a broader decision | ADR-008 refines ADR-002 |

Inverse relations auto-generated: store `(A, supersedes, B)` → also store `(B, superseded_by, A)`.

## Dependency Graph

```
                    ┌──────────────┐
                    │ 1. ADR Format │
                    │   & Schema    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ 2. Engine │  │ 3. Seed  │  │ 4. Skill │
      │ (graph +  │  │   Data   │  │   Defs   │
      │  FTS5)    │  │          │  │          │
      └──────┬───┘  └──────┬───┘  └──────┬───┘
              │            │            │
              └────────┬───┘            │
                       ▼                │
              ┌──────────────┐          │
              │ 5. Recall    │◄─────────┘
              │    Skill     │
              └──────┬───────┘
                     │
              ┌──────┴───────┐
              ▼              ▼
      ┌──────────┐   ┌──────────┐
      │ 6. Record │   │ 7. Auto- │
      │   Skill   │   │  Record  │
      │           │   │  Hook    │
      └──────────┘   └──────────┘
```

## Phases

### Phase 1: Foundation (Tasks 1-3)
Format, dual-index engine, seed data.
**Checkpoint:** `python bin/decision-engine.py search "agent"` and `python bin/decision-engine.py graph ADR-001` both return results.

### Phase 2: Retrieval (Tasks 4-5)
Skills that query both indexes and merge results.
**Checkpoint:** `/frontier-brain:recall "state management"` returns ranked ADRs with relationship context.

### Phase 3: Auto-Recording (Tasks 6-7)
Record skill + auto-detect hook. Full autonomous loop.
**Checkpoint:** Make decision in conversation → ADR auto-created → recallable in new session.

## File Structure (Final)

```
frontier-brain/
├── .claude/
│   ├── skills/
│   │   ├── decision-recall/
│   │   │   └── SKILL.md
│   │   └── decision-record/
│   │       └── SKILL.md
│   ├── commands/
│   │   ├── recall.md
│   │   └── record.md
│   └── settings.json
├── bin/
│   └── decision-engine.py      # CLI: index, search, graph, next-id
├── hooks/
│   └── decision-detect.js      # UserPromptSubmit hook (lightweight JS)
├── decisions/
│   ├── TEMPLATE.md
│   ├── SCHEMA.md
│   ├── ADR-001-*.md
│   ├── ADR-002-*.md
│   ├── graph.db                # graphdb relationships (gitignored)
│   └── search.db               # SQLite FTS5 index (gitignored)
├── lib/
│   └── graphdb/                # vendored from ~/Downloads/graphdb-2020.2.4
├── pyproject.toml              # deps: pyyaml (graphdb vendored)
├── tasks/
│   ├── plan.md
│   └── todo.md
└── CLAUDE.md
```

## Dependencies

| Package | Source | Why |
|---------|--------|-----|
| `graphdb` | Vendored from `~/Downloads/graphdb-2020.2.4` | Relationship graph |
| `pyyaml` | PyPI | YAML frontmatter parsing |
| `dill` | PyPI (graphdb dep) | Object serialization for graphdb |
| `generators` | PyPI (graphdb dep) | graphdb dep |
| `strict_functions` | PyPI (graphdb dep) | graphdb dep |

Hook (`decision-detect.js`) is pure JS — no npm deps. Regex-only, <100ms.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| graphdb deps (`generators`, `strict_functions`) fail behind proxy | Blocks graph layer | Vendor entire graphdb + deps, or refactor to remove deps |
| Auto-record creates noisy/low-quality ADRs | Cluttered decision history | Claude's record skill has quality heuristics; easy to delete bad ADRs |
| graphdb 2020 vintage, unmaintained | Bugs, no Python 3.12+ testing | Vendor + patch if needed; simple codebase (~500 lines) |
| `dill` serialization fragile across Python versions | Graph DB unreadable after upgrade | Store ADR IDs as strings (not complex objects) — dill handles strings fine |
| Two DBs drift out of sync | Inconsistent recall results | Single `index` command rebuilds both from markdown source of truth |
