---
id: ADR-007
title: Markdown Files as Source of Truth Over Databases
status: accepted
date: 2026-04-27
tags: [architecture, storage, markdown, gitops]
supersedes: []
related: [ADR-001]
project: frontier-brain
---

## Context

With two databases (graph.db, search.db) plus markdown files, need to establish which is authoritative. Databases could drift from markdown or vice versa.

## Considered Options

### Database as Source of Truth
- Pro: Single write path, consistent
- Con: Binary files, not human-readable, not git-diffable, recovery harder

### Markdown as Source of Truth
- Pro: Human-readable, git-diffable, editable in any editor, databases fully rebuildable
- Con: Must rebuild indexes after manual edits

## Decision

Markdown files in `decisions/` are the source of truth. Both databases are derived indexes — delete and rebuild from markdown at any time via `python bin/decision-engine.py index`. Databases are gitignored.

## Consequences

Manual edits to ADR files require re-running `index`. Both .db files in .gitignore. Recovery is always possible from markdown alone.
