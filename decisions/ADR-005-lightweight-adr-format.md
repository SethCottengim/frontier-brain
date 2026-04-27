---
id: ADR-005
title: Lightweight ADR Format Over SEMPL Template
status: accepted
date: 2026-04-27
tags: [format, adr, schema, markdown]
supersedes: []
related: [ADR-003]
project: frontier-brain
---

## Context

SEMPL ADR template has 12+ sections including Document Management, Ownership, Agent Impact, Standards Alignment, Mental/Physical State. Overkill for quick decision capture during Claude sessions.

## Considered Options

### Full SEMPL ADR Template
- Pro: Comprehensive, matches existing team format
- Con: Too heavy for auto-recording, 12+ sections, friction

### Lightweight YAML Frontmatter + 4 Sections
- Pro: 8 frontmatter fields, 4 body sections, parseable by pyyaml, fast to write
- Con: Less detail than full SEMPL format

## Decision

Lightweight format: YAML frontmatter (id, title, status, date, tags, supersedes, related, project) + 4 body sections (Context, Considered Options, Decision, Consequences). 8 frontmatter fields max.

## Consequences

ADRs are concise (10-20 lines body). Can auto-promote to full SEMPL format later if needed (stretch goal S4). Frontmatter parseable by `yaml.safe_load()`.
