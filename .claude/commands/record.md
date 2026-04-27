---
description: Record a decision from this conversation as an ADR
---

Use the decision-record skill to capture the most recent decision from this conversation.

1. Identify the decision made in recent conversation context
2. Check quality gate — skip if trivial or temporary
3. Run `python bin/decision-engine.py search` to check for existing related ADRs
4. Run `python bin/decision-engine.py next-id` to get next ID
5. Write the ADR file and run `python bin/decision-engine.py index`
6. Confirm with one line — do not ask for review
