---
description: Search past architectural decisions by topic or ID
---

Use the decision-recall skill to find relevant past decisions.

Query: $ARGUMENTS

1. Run `python bin/decision-engine.py search "$ARGUMENTS"` for text matches
2. For top results, run `python bin/decision-engine.py graph <id>` for relationship context
3. Read the full ADR files for top 3 matches
4. Present a summary table + relationship map + key excerpts
