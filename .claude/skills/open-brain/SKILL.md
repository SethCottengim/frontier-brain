---
name: open-brain
description: Reindex decision records, regenerate the Decision Knowledge Graph visualization, print summary stats, and open it in the browser. Use when user wants to see their decision graph, says "open brain", or wants to visualize decisions.
---

Open the Decision Knowledge Graph. Run these steps in order:

1. Reindex all decision markdown files into brain.db:
   ```bash
   python3 ~/.claude/frontier-brain/bin/decision-engine.py index
   ```

2. Query stats from brain.db for the summary line:
   ```bash
   python3 -c "
   import sqlite3, json
   conn = sqlite3.connect(str(__import__('pathlib').Path.home() / '.claude/decisions/brain.db'))
   rows = conn.execute('SELECT type, COUNT(*) FROM decisions GROUP BY type').fetchall()
   counts = dict(rows)
   total = sum(counts.values())
   parts = [f\"{counts.get(t, 0)} {t}\" for t in ['decision', 'knowledge', 'context'] if counts.get(t, 0)]
   print(f\"Brain: {total} records — {', '.join(parts)}\")
   conn.close()
   "
   ```

3. Regenerate and open the graph:
   ```bash
   python3 ~/.claude/frontier-brain/bin/visualize.py --open
   ```

4. Print the stats line from step 2, then confirm the graph opened. One line total. Example:
   "Brain: 42 records — 30 decision, 8 knowledge, 4 context — graph opened"
