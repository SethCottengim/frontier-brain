# Decision Knowledge Graph — Task List

## Phase 1: Foundation

### Task 1: ADR Schema & Template
**Status:** done
**Depends on:** nothing
**Delivers:** ADR markdown format definition + template file + schema docs

**Work:**
- Define YAML frontmatter schema (id, title, status, date, tags, supersedes, related, project)
- Create `decisions/TEMPLATE.md` with all sections
- Create `decisions/SCHEMA.md` documenting field definitions, valid values, conventions
- Document relationship types and their semantics
- Status values: `proposed | accepted | superseded | deprecated`

**Acceptance Criteria:**
- [ ] Template exists at `decisions/TEMPLATE.md`
- [ ] Schema docs exist at `decisions/SCHEMA.md`
- [ ] Frontmatter is valid YAML parseable by `pyyaml`
- [ ] Relationship types documented with examples
- [ ] Format lighter than SEMPL ADR template (≤8 frontmatter fields)

**Verification:** `python -c "import yaml; yaml.safe_load(open('decisions/TEMPLATE.md').read().split('---')[1])"` — no errors.

---

### Task 2: Hybrid Index Engine (graphdb + FTS5)
**Status:** done
**Depends on:** Task 1 (needs schema)
**Delivers:** `bin/decision-engine.py` — CLI wrapping both graphdb and SQLite FTS5

**Work:**
- Vendor graphdb from `~/Downloads/graphdb-2020.2.4/graphdb/` into `lib/graphdb/`
- Verify graphdb works with current Python (test basic store/query)
- Install graphdb deps (`dill`, `generators`, `strict_functions`) via uv/pip
- Create `bin/decision-engine.py` with subcommands:
  - `index` — rebuild both DBs from `decisions/*.md`
    - Parse YAML frontmatter with pyyaml
    - FTS5: create `search.db` with full-text index on title + body + tags
    - Graph: create `graph.db` with relationship triples from frontmatter
    - Auto-create inverse relations (supersedes → superseded_by)
  - `search <query>` — FTS5 full-text search, return ranked JSON
  - `graph <id>` — graphdb traversal, return all connected decisions as JSON
  - `related <id>` — combined: graph neighbors + FTS5 on shared tags
  - `next-id` — read max existing ID, return next sequential
- Create `pyproject.toml` with deps
- Output: JSON to stdout (consumable by skill scripts)

**Acceptance Criteria:**
- [ ] `python bin/decision-engine.py index` creates both `graph.db` and `search.db`
- [ ] `python bin/decision-engine.py search "state management"` returns ranked JSON
- [ ] `python bin/decision-engine.py graph ADR-001` returns connected decisions
- [ ] `python bin/decision-engine.py related ADR-001` returns merged results
- [ ] `python bin/decision-engine.py next-id` returns next sequential ID
- [ ] Handles 0 files gracefully
- [ ] Both DBs rebuildable from markdown (delete, re-run, same results)
- [ ] Inverse relations auto-created in graph

**Verification:**
1. Create 3+ test ADR files with cross-references
2. `python bin/decision-engine.py index` — no errors
3. `python bin/decision-engine.py search "test"` — returns matches
4. `python bin/decision-engine.py graph ADR-001` — shows relationships
5. Delete both .db files, re-index, same results

---

### Task 3: Seed with Existing Decisions
**Status:** done
**Depends on:** Task 1 (format) + Task 2 (engine, to verify)
**Delivers:** 8-12 ADR files distilled from existing SEMPL ADRs + CLAUDE.md

**Work:**
- Extract key decisions from:
  - `sempl-core/resources/docs/architecture/decisions/` (19 existing ADRs)
  - Workspace `CLAUDE.md` technology decisions table
- Convert to lightweight format (distill, not copy)
- Assign sequential IDs (ADR-001 through ADR-0XX)
- Establish relationship graph:
  - Strands migration supersedes LangChain decision
  - Graph DB standardization relates to agent framework choice
  - GitOps relates to CI/CD choices
  - etc.
- Run indexer to populate both DBs

**Acceptance Criteria:**
- [ ] ≥8 decision files in `decisions/`
- [ ] Each has valid frontmatter matching schema
- [ ] Relationship graph has ≥10 edges across decisions
- [ ] Decisions span multiple projects (agents, ui, infra, methodology)
- [ ] Both indexes populated and queryable

**Verification:**
1. `python bin/decision-engine.py index` — all files parse
2. `python bin/decision-engine.py search "agent"` — returns ≥2 results
3. `python bin/decision-engine.py graph ADR-001` — shows ≥1 connection

---

## CHECKPOINT: Phase 1 Complete
**Gate:** Both `search` and `graph` commands return meaningful results from seeded data.

---

## Phase 2: Retrieval

### Task 4: Skill Definitions
**Status:** done
**Depends on:** nothing (can parallel with Phase 1)
**Delivers:** SKILL.md files + command shortcuts

**Work:**
- Create `.claude/skills/decision-recall/SKILL.md`:
  - When to use: understanding past decisions, checking for prior art, "what did we decide about X?"
  - Workflow: search engine → read top matches → present with graph context
  - Example invocations
  - Checklist format (matching gitnexus skill pattern)
- Create `.claude/skills/decision-record/SKILL.md`:
  - When to use: auto-invoked by hook, or manually after making a decision
  - Workflow: extract from conversation → next-id → write ADR → index
  - No human review step — write directly
  - Quality heuristics (what makes a good ADR vs noise)
- Create `.claude/commands/recall.md` — `/frontier-brain:recall <topic>`
- Create `.claude/commands/record.md` — `/frontier-brain:record`

**Acceptance Criteria:**
- [ ] Skills follow SKILL.md format (YAML frontmatter: name, description)
- [ ] Record skill explicitly says NO human review needed
- [ ] Record skill includes quality heuristics (skip trivial decisions)
- [ ] Recall skill instructs dual-query (FTS5 + graph)
- [ ] Commands exist with descriptions

**Verification:** Start new session in frontier-brain, confirm skills appear in available list.

---

### Task 5: Recall Skill Implementation
**Status:** done
**Depends on:** Task 2 (engine) + Task 4 (skill def)
**Delivers:** Working dual-index recall — text search + graph traversal merged

**Work:**
- Recall flow:
  1. User or context triggers recall
  2. Run `python bin/decision-engine.py search "<query>"` → ranked text matches
  3. For top results, run `python bin/decision-engine.py graph <id>` → relationship context
  4. Merge: show matched decisions + their graph neighbors
  5. Read full ADR files for top 3 matches
  6. Present: table of results + relationship map + relevant excerpts
- Edge cases: no results, single result, query too broad
- Skill should auto-trigger when Claude detects architectural questions

**Acceptance Criteria:**
- [ ] `/frontier-brain:recall "state management"` returns relevant ADRs
- [ ] Results include both text matches AND graph-connected decisions
- [ ] Relationship chain visible (A supersedes B, relates to C)
- [ ] Full ADR content for top matches
- [ ] No results case handled gracefully

**Verification:** Run 3 queries against seed data:
1. Topic search ("authentication") → text matches
2. ID-based ("ADR-001") → graph traversal
3. Broad ("architecture") → multiple results with relationships

---

## CHECKPOINT: Phase 2 Complete
**Gate:** Recall returns both text matches and graph relationships in live session.

---

## Phase 3: Auto-Recording

### Task 6: Record Skill Implementation
**Status:** done
**Depends on:** Task 1 (template) + Task 2 (engine) + Task 4 (skill def)
**Delivers:** Autonomous record flow — Claude extracts + writes + indexes without human review

**Work:**
- Record flow (invoked by hook or manually):
  1. Get next ID: `python bin/decision-engine.py next-id`
  2. Extract from conversation context:
     - Context: what problem/question led to decision
     - Options considered (if any were discussed)
     - Decision: what was chosen
     - Consequences: what changes
     - Tags: infer from topic
     - Project: infer from working directory / files discussed
     - Relationships: check existing ADRs for supersedes/related
  3. Write ADR file to `decisions/ADR-XXX-slug.md`
  4. Run `python bin/decision-engine.py index` to update both DBs
  5. Brief one-line confirmation (not a full review)
- Quality heuristics (skip if):
  - Decision is trivial (variable naming, formatting)
  - Decision is temporary ("let's try X for now")
  - No real alternatives were considered
  - Already recorded (check existing ADRs first)
- Relationship detection:
  - Before recording, search existing ADRs for related topics
  - If new decision supersedes an old one, set `supersedes:` and update old ADR status

**Acceptance Criteria:**
- [ ] Creates valid ADR file with all sections populated
- [ ] Auto-increments ID
- [ ] Infers tags and project from context
- [ ] Detects relationships to existing ADRs
- [ ] Updates both indexes after recording
- [ ] Skips trivial decisions (quality filter)
- [ ] No confirmation prompt — just writes

**Verification:** In a session:
1. Discuss "should we use X or Y for Z?"
2. Decide "let's go with X"
3. ADR file appears in `decisions/`
4. Both indexes updated
5. Recallable immediately

---

### Task 7: Decision Detection Hook (Auto-Trigger)
**Status:** done
**Depends on:** Task 6 (record skill must work first)
**Delivers:** UserPromptSubmit hook that auto-triggers recording

**Work:**
- Create `hooks/decision-detect.js` — lightweight JS hook (matches gitnexus pattern)
- Triggers on UserPromptSubmit
- Detection regex for decision signals:
  - Commitment: "let's go with", "decided to", "choosing", "we'll use", "approved"
  - Comparison: "X over Y", "instead of", "rather than"
  - Architecture: "architecture", "framework", "pattern", "approach", "stack"
  - Combined: commitment verb + architecture noun
- If detected → emit `additionalContext`:
  ```
  Decision detected in user message. Auto-record this decision:
  1. Run: python bin/decision-engine.py next-id
  2. Extract context, options, decision, consequences from conversation
  3. Write ADR file and run: python bin/decision-engine.py index
  Do not ask for confirmation.
  ```
- Must be fast (<100ms) — regex only, no subprocess, no I/O beyond stdin
- Register in project `.claude/settings.json` hooks

**Acceptance Criteria:**
- [ ] Hook fires on "let's go with React for the frontend" (true positive)
- [ ] Hook fires on "choosing Strands over LangChain" (true positive)
- [ ] Hook does NOT fire on "let's go get lunch" (true negative)
- [ ] Hook does NOT fire on "I decided to take a break" (true negative)
- [ ] additionalContext instructs Claude to auto-record without confirmation
- [ ] Completes in <100ms
- [ ] Registered in settings.json hooks config

**Verification:** Test matrix:

| Prompt | Should Fire? |
|--------|-------------|
| "let's go with MobX for state management" | YES |
| "I've decided we should use PostgreSQL instead of MySQL" | YES |
| "choosing the microservices approach over monolith" | YES |
| "let's go to lunch" | NO |
| "I decided to take a walk" | NO |
| "what do you think about Redis?" | NO (question, not decision) |
| "can you explain the auth flow?" | NO |

---

## CHECKPOINT: Phase 3 Complete
**Gate:** Full autonomous loop in live session:
1. User makes decision in conversation
2. Hook detects → instructs Claude
3. Claude auto-records ADR (no confirmation)
4. New session → `/frontier-brain:recall` finds it

---

## Stretch Goals (Post-MVP)

### S1: PreToolUse Recall Hook
Auto-inject decision context when Claude searches for architecture-related code.
Similar to gitnexus PreToolUse — intercept grep/search, augment with related decisions.

### S2: Decision Decay Detection
Periodic check: are any accepted ADRs >6 months old with no superseding decision?
Flag for review — decisions may be stale.

### S3: Cross-Project Decision Sync
If running in sempl-core, also search frontier-brain decisions.
Shared decisions index across workspace projects.

### S4: SEMPL ADR Bridge
Two-way sync between lightweight frontier-brain ADRs and heavyweight SEMPL ADRs.
Auto-promote important decisions to full SEMPL format.
