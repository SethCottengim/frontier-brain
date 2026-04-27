---
id: ADR-003
title: Autonomous ADR Recording Without Human Review
status: accepted
date: 2026-04-27
tags: [workflow, automation, hooks, agent-skills]
supersedes: []
related: [ADR-004, ADR-005]
project: frontier-brain
---

## Context

Need to capture decisions made during Claude Code sessions. Manual recording adds friction — decisions get lost. Question: should Claude ask for confirmation before writing ADRs?

## Considered Options

### Manual Review Before Recording
- Pro: Higher quality, human-verified accuracy
- Con: Friction kills adoption, defeats "autonomous memory" goal

### Fully Autonomous (No Review)
- Pro: Zero friction, decisions captured as they happen
- Con: Risk of noisy/low-quality ADRs

## Decision

Fully autonomous. Claude writes ADR directly without confirmation prompt. Quality gate in the record skill filters trivial/temporary decisions. Humans can edit or delete bad ADRs after the fact.

## Consequences

Record skill must have quality heuristics to avoid noise. One-line confirmation only ("Recorded ADR-XXX: title"). Humans retain edit/delete power but never block the recording flow.
