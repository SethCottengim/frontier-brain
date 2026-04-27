---
id: ADR-001
title: Hybrid Graph + FTS5 Storage for Decision Index
status: accepted
date: 2026-04-27
tags: [architecture, storage, graph-db, fts5, sqlite]
supersedes: []
related: [ADR-002]
project: frontier-brain
---

## Context

Need to store and retrieve architectural decisions. Two access patterns: "find decisions about X" (text search) and "what relates to what" (graph traversal). Neither pattern alone covers both needs.

## Considered Options

### FTS5 Only
- Pro: Zero external deps, stdlib sqlite3
- Con: No relationship traversal, can't answer "what does ADR-001 supersede?"

### Graph DB Only
- Pro: Rich relationship queries, chainable traversal
- Con: No ranked text search, can't answer "find decisions about authentication"

### Hybrid: Graph + FTS5
- Pro: Both access patterns covered, single CLI wraps both
- Con: Two databases to maintain, slightly more complexity

## Decision

Hybrid approach — SQLite-based graph DB for relationships + SQLite FTS5 for full-text search. Both rebuilt from markdown source of truth via single `index` command. Single CLI (`bin/decision-engine.py`) wraps both.

## Consequences

Two .db files in decisions/ directory (gitignored, rebuildable). Engine CLI must handle both indexes atomically during rebuild.
