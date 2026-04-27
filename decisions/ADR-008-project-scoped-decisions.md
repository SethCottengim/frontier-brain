---
id: ADR-008
title: Project-Scoped Decision Tracking in frontier-brain
status: accepted
date: 2026-04-27
tags: [scope, architecture, project-direction]
supersedes: []
related: []
project: frontier-brain
---

## Context

Workspace has multiple projects (sempl-core, autobot, OASIS, etc.). Decisions could be tracked per-project or centrally. Need to define scope for frontier-brain's decision graph.

## Considered Options

### Central Decision Store for All Projects
- Pro: Single place to find all decisions, cross-project relationships visible
- Con: Complex, scope creep, ownership unclear

### frontier-brain Scoped Only (Start Here)
- Pro: Simple, self-contained, prove the concept first
- Con: Can't query across projects initially

## Decision

Start with frontier-brain scope only. Track decisions made in this project. Use `project` field in frontmatter to tag which project a decision applies to. Cross-project sync is a stretch goal (S3).

## Consequences

Only decisions made in frontier-brain sessions get auto-recorded here. Other projects can adopt the pattern independently later.
