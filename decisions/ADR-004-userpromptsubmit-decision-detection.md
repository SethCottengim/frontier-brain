---
id: ADR-004
title: UserPromptSubmit Hook for Decision Detection
status: accepted
date: 2026-04-27
tags: [hooks, automation, detection, workflow]
supersedes: []
related: [ADR-003, ADR-005]
project: frontier-brain
---

## Context

For autonomous recording to work, need to detect when a decision is being made. Options: manual trigger only, PostToolUse detection, or UserPromptSubmit pre-scan.

## Considered Options

### Manual Trigger Only
- Pro: Precise, no false positives
- Con: Relies on human remembering to trigger — same friction as manual recording

### UserPromptSubmit Hook
- Pro: Scans user message before Claude sees it, injects additionalContext to auto-record
- Con: Regex-based detection has false positive/negative risk

### PostToolUse Detection
- Pro: Could detect decisions from Claude's output
- Con: PostToolUse only sees tool calls, not conversational decisions

## Decision

UserPromptSubmit hook with regex detection. Matches commitment verbs ("let's go with", "decided to", "choosing") combined with architecture nouns ("framework", "pattern", "approach"). Injects recording instruction via additionalContext. Same pattern as gitnexus hook.

## Consequences

Hook must be fast (<100ms) — regex only, no subprocess. False positives get filtered by record skill quality gate. Hook registered in .claude/settings.json.
