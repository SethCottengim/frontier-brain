---
name: decision-harvest
description: "Scan entire conversation for engineering decisions, knowledge, and context. Batch-identify and record them to ~/.claude/decisions/. Use to retroactively capture decisions from long chats."
---

# Decision Harvest

Scan the full conversation and extract all significant engineering decisions, knowledge, and context worth preserving.

## Workflow

```
1. Scan entire conversation for:
   - Architecture/stack decisions (chose X over Y because Z)
   - Knowledge learned through experience (gotchas, env quirks, workarounds)
   - Project context (goals, constraints, scope definitions)

2. Skip:
   - Trivial choices (naming, formatting)
   - Temporary/experimental decisions ("let's try X for now")
   - Things already recorded (check first)

3. Present candidates as numbered list:
   | # | Type | Title | Why it matters |
   |---|------|-------|---------------|
   | 1 | decision | ... | ... |
   | 2 | knowledge | ... | ... |

4. Ask: "Record all, or give me numbers to skip?"

5. For each approved candidate:
   a. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py next-id
   b. Infer: project (from git remote or conversation context), tags, relationships
   c. Write record to ~/.claude/decisions/NNN-slug.md
   d. Check against already-recorded candidates for related[] links

6. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py index

7. Summary: "Harvested N decisions. IDs: #X, #Y, #Z"
```

## Record Template

```markdown
---
id: <N>
title: <Title>
type: decision | knowledge | context
status: active
date: <YYYY-MM-DD of today, not when decision was made>
project: <inferred from conversation>
tags: [<inferred>]
affects: []
recorded_by: <$USER>
supersedes: []
related: [<other harvested IDs if connected>]
---
What was chosen/learned and why. 2-5 sentences.
```

## Important

- **DO ask for confirmation** before recording (unlike single-record skill). User picks which to keep.
- Cross-link harvested records to each other via `related[]` when they connect.
- Infer project from conversation context — look for git remotes, directory paths, project names mentioned.
- Date is today (when recorded), not when decision was originally made.
