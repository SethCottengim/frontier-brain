---
name: decision-record
description: "Records architectural and tool decisions as ADR files. Auto-invoked by decision detection hook or manually via /frontier-brain:record. Writes ADR directly — no human review needed."
---

# Decision Record

## When to Use

- Auto-triggered by decision detection hook (UserPromptSubmit)
- Manually after making a significant decision in conversation
- `/frontier-brain:record` command

## Quality Gate — Skip If

- Decision is trivial (variable naming, formatting, whitespace)
- Decision is temporary ("let's try X for now and revisit")
- No real alternatives were considered or existed
- Already recorded (search existing ADRs first)

## Workflow

```
1. Run: python bin/decision-engine.py search "<decision topic>"  → check not already recorded
2. Run: python bin/decision-engine.py next-id                    → get next sequential ID
3. Extract from conversation context:
   - Context: what problem/question led to decision
   - Options considered (if discussed)
   - Decision: what was chosen
   - Consequences: what changes
   - Tags: infer from topic (lowercase, hyphenated)
   - Project: infer from working directory / files discussed
   - Relationships: check existing ADRs for supersedes/related
4. Write ADR file to decisions/ADR-XXX-slug.md
5. If decision supersedes an existing ADR, update old ADR status to "superseded"
6. Run: python bin/decision-engine.py index                      → update both indexes
7. One-line confirmation: "Recorded ADR-XXX: <title>"
```

## Checklist

```
- [ ] Check quality gate — skip trivial decisions
- [ ] Search for existing related ADRs
- [ ] Get next ID from decision-engine
- [ ] Extract context, options, decision, consequences from conversation
- [ ] Infer tags and project
- [ ] Detect relationships (supersedes, related_to)
- [ ] Write ADR file in decisions/ directory
- [ ] Update superseded ADR status if applicable
- [ ] Run index to update both databases
- [ ] Confirm with one line (no review prompt)
```

## ADR Template

```markdown
---
id: ADR-XXX
title: <Title>
status: accepted
date: <today YYYY-MM-DD>
tags: [<inferred>]
supersedes: [<if applicable>]
related: [<if found>]
project: <inferred>
---

## Context
<extracted from conversation>

## Considered Options
### <Option A>
- Pro: ...
- Con: ...
### <Option B>
- Pro: ...
- Con: ...

## Decision
<what was chosen and why>

## Consequences
<what changes>
```

## Important

- **Do NOT ask for confirmation.** Write the ADR directly.
- **Do NOT show the full ADR content for review.** Just confirm recording.
- Keep ADRs concise — 10-20 lines of body content max.
- If unsure whether something qualifies as a decision, err on the side of recording it.
