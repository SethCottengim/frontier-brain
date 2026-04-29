---
name: decision-cross-link
description: "Discover cross-project edge candidates between decision records. Scores pairs by shared tags + text similarity, presents ranked candidates for user approval, writes approved edges to frontmatter."
---

# Cross-Link Discovery

## When to Use

- "Find connections between projects"
- "What decisions bridge frontier-brain and OASIS?"
- "Run cross-link discovery"
- After recording a new decision, to check for cross-project relationships

## Workflow

```
1. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py cross-link
   Options: --threshold 0.1 (default) | --top N | --record <id>
2. Present candidates to user grouped by strength:
   - Strong (>0.3): likely genuine cross-project relationship
   - Moderate (0.15-0.3): plausible, needs judgment
   - Weak (0.1-0.15): mostly tag co-occurrence noise
3. For each candidate, show: source record, target record, score, rationale
4. User approves/rejects/comments on each
5. For approved edges: add target_id to source record's `related:` field and vice versa
6. Reindex: python3 ~/.claude/frontier-brain/bin/decision-engine.py index
7. Regenerate graph: python3 ~/.claude/frontier-brain/bin/visualize.py --open
```

## Checklist

```
- [ ] Run cross-link command
- [ ] Present candidates grouped by strength
- [ ] Get user approval for each proposed edge
- [ ] Write approved edges to both record files' `related:` fields
- [ ] Reindex brain.db
- [ ] Regenerate and open graph
```

## Presentation Format

```markdown
### Cross-Project Candidates

**Strong (>0.3):**
- #15 (frontier-brain) <-> #27 (OASIS) — score: 0.43
  Rationale: shared primary_tag: migration; shared tags: architecture, migration

**Moderate (0.15-0.3):**
- (none)

**Weak (0.1-0.15):**
- #3 (frontier-brain) <-> #21 (OASIS) — score: 0.12
  Rationale: shared tags: architecture

Approve edges? (list IDs, "all strong", or "none")
```

## Edge Cases

- **No candidates above threshold**: "No cross-project connections found above threshold 0.1"
- **All weak**: Tell user tag nodes already bridge these visually, explicit edges optional
- **User wants lower threshold**: Rerun with `--threshold 0.05`
