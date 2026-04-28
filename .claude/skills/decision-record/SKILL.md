---
name: decision-record
description: "Records engineering decisions, knowledge, and context as markdown records. Auto-invoked by decision detection hook or manually via /frontier-brain:record. Writes record directly — no human review needed."
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
- Already recorded (search existing records first)

## Workflow

```
1. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py search "<topic>"  → check not already recorded
2. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py next-id            → get next sequential ID
3. Extract from conversation context:
   - Title: concise summary
   - Type: decision | knowledge | context
   - Tags: infer from topic (lowercase, hyphenated)
   - Project: infer from working directory / git remote
   - Affects: file paths affected (optional)
   - Body: what was chosen/learned and why (2-5 sentences)
   - Relationships: check existing records for supersedes/related
4. Write record file to ~/.claude/decisions/NNN-slug.md
5. If record supersedes an existing one, update old record status to "superseded"
6. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py index  → update brain.db
7. One-line confirmation: "Recorded #N: <title>"
```

## Checklist

```
- [ ] Check quality gate — skip trivial decisions
- [ ] Search for existing related records
- [ ] Get next ID from decision-engine
- [ ] Extract title, type, tags, project, body from conversation
- [ ] Detect relationships (supersedes, related)
- [ ] Write record file to ~/.claude/decisions/
- [ ] Update superseded record status if applicable
- [ ] Run index to update brain.db
- [ ] Confirm with one line (no review prompt)
```

## Record Template

```markdown
---
id: <N>
title: <Title>
type: decision
status: active
date: <today YYYY-MM-DD>
project: <inferred>
tags: [<inferred>]
affects: []
recorded_by: <$USER>
supersedes: []
related: []
---
Free-text body. 2-5 sentences. What was chosen/learned and why.
```

## Important

- **Do NOT ask for confirmation.** Write the record directly.
- **Do NOT show the full record content for review.** Just confirm recording.
- Keep records concise — 2-5 sentences of body content.
- If unsure whether something qualifies, err on the side of recording it.
