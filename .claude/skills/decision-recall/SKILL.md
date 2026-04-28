---
name: decision-recall
description: "Use when the user asks about past decisions, architecture choices, or 'what did we decide about X?' Queries FTS5 + graph in brain.db to retrieve relevant records with relationship context."
---

# Decision Recall

## When to Use

- "What did we decide about X?"
- "Have we made a decision about state management?"
- "What's the history of our auth choices?"
- "What decisions relate to record 5?"
- Any architectural question where prior decisions may exist

## Workflow

```
1. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py search "<query>"  → FTS5 ranked matches
2. For top results, run: python3 ~/.claude/frontier-brain/bin/decision-engine.py graph <id>  → relationship context
3. Run: python3 ~/.claude/frontier-brain/bin/decision-engine.py related <id>  → combined neighbors + tag matches
4. Read full record files for top 3 matches from ~/.claude/decisions/
5. Present results with relationship chain
```

## Checklist

```
- [ ] Search by topic text via decision-engine search
- [ ] Get graph context for top matches via decision-engine graph
- [ ] Read full record content for top 3
- [ ] Show relationship chain (supersedes, related)
- [ ] If no results, say so — don't hallucinate decisions
```

## Presentation Format

```markdown
### Relevant Decisions

| ID | Title | Type | Status | Relevance |
|----|-------|------|--------|-----------|
| 1 | ... | decision | active | text match |
| 3 | ... | knowledge | active | related to 1 |

### Relationship Map
1 ──supersedes──→ (none)
1 ──related──→ 3

### Key Context
[Excerpts from top matches]
```

## Edge Cases

- **No results**: "No recorded decisions found for this topic."
- **Single result**: Show it + graph neighbors
- **Query too broad**: Show top 5, suggest narrowing
- **ID-based query**: Skip text search, go straight to graph traversal
