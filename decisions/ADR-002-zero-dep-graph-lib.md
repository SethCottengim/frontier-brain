---
id: ADR-002
title: Zero-Dependency Graph Library Instead of Vendored graphdb
status: accepted
date: 2026-04-27
tags: [architecture, dependencies, graph-db, sqlite]
supersedes: []
related: [ADR-001]
project: frontier-brain
---

## Context

Original plan was to vendor CodyKochmann/graphdb (2020.2.4) from ~/Downloads. Requires `dill`, `generators`, `strict_functions` — none installed, corporate proxy makes pip unreliable. graphdb uses dill serialization for arbitrary Python objects, but we only store string ADR IDs.

## Considered Options

### Vendor graphdb + Install Deps
- Pro: Battle-tested library with chainable traversal API
- Con: 3 transitive deps behind corporate proxy, dill serialization overkill for strings

### Write Minimal Graph Engine
- Pro: Zero deps beyond stdlib sqlite3, simpler than graphdb, fits our exact use case
- Con: No chainable V/VList traversal API

## Decision

Write minimal `lib/graphdb/` — same SQLite schema (objects + relations tables), same core API (store_relation, find, relations_of, relations_to), but stores plain strings instead of dill-serialized objects. ~130 lines vs ~500.

## Consequences

No external dependency risk. Lose chainable `db["ADR-001"].related_to.supersedes.to(list)` syntax — use explicit `find()` calls instead. Acceptable tradeoff since engine CLI handles all traversal internally.
