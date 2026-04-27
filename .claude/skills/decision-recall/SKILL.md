---
name: decision-recall
description: "Use when the user asks about past decisions, architecture choices, or 'what did we decide about X?' Queries dual-index (full-text + graph) to retrieve relevant ADRs with relationship context."
---

# Decision Recall

## When to Use

- "What did we decide about X?"
- "Have we made a decision about state management?"
- "What's the history of our auth choices?"
- "What decisions relate to ADR-005?"
- Any architectural question where prior decisions may exist
- Auto-trigger when detecting architecture/design questions

## Workflow

```
1. Run: python bin/decision-engine.py search "<query>"     → FTS5 ranked text matches
2. For top results, run: python bin/decision-engine.py graph <id>  → relationship context
3. Run: python bin/decision-engine.py related <id>          → combined neighbors + tag matches
4. Read full ADR files for top 3 matches
5. Present results with relationship chain
```

## Checklist

```
- [ ] Search by topic text via decision-engine search
- [ ] Get graph context for top matches via decision-engine graph
- [ ] Read full ADR content for top 3
- [ ] Show relationship chain (supersedes, related_to, etc.)
- [ ] If no results, say so — don't hallucinate decisions
```

## Presentation Format

```markdown
### Relevant Decisions

| ID | Title | Status | Relevance |
|----|-------|--------|-----------|
| ADR-001 | ... | accepted | text match |
| ADR-003 | ... | accepted | related to ADR-001 |

### Relationship Map
ADR-001 ──supersedes──→ ADR-000
ADR-001 ──related_to──→ ADR-003

### Key Context
[Excerpts from top matches]
```

## Edge Cases

- **No results**: "No recorded decisions found for this topic."
- **Single result**: Show it + graph neighbors
- **Query too broad**: Show top 5, suggest narrowing
- **ID-based query**: Skip text search, go straight to graph traversal
