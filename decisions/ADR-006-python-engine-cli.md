---
id: ADR-006
title: Python CLI for Decision Engine
status: accepted
date: 2026-04-27
tags: [tooling, python, cli, architecture]
supersedes: []
related: [ADR-001, ADR-002]
project: frontier-brain
---

## Context

Need a tool to index, search, and traverse decision files. Could be Python (matches user stack), Node (matches gitnexus), or shell scripts.

## Considered Options

### Node.js CLI
- Pro: Same language as Claude Code hooks, could reuse gitnexus patterns
- Con: User stack is Python-heavy, graphdb is Python, would need node deps

### Shell Scripts
- Pro: No runtime deps
- Con: Complex FTS5 + graph logic ugly in bash, poor JSON handling

### Python CLI
- Pro: Matches user stack (Django, Strands, uv), graphdb is Python, pyyaml available, sqlite3 in stdlib
- Con: Hooks still need JS (Claude Code requirement)

## Decision

Python CLI at `bin/decision-engine.py`. Single file, subcommands: index, search, graph, related, next-id. JSON output to stdout. Skills/hooks shell out to it.

## Consequences

Skills call `python bin/decision-engine.py <cmd>`. Hook (decision-detect.js) is pure JS regex — no Python subprocess needed for detection, only for recording.
