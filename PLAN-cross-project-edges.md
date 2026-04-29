# Cross-Project Edges via Tag Nodes in Frontier-Brain

## Goal
Add controlled tag vocabulary, tag nodes in graph visualization, and cross-project edge discovery to frontier-brain. Currently 28 decision records across 2 projects have zero cross-project connections — tag nodes become organic bridges while explicit gold-dashed edges handle direct causal relationships.

## Decisions

| Decision | Choice |
|----------|--------|
| Tag registry format | Flat YAML with name, axis, description |
| Granularity rule | "Distinct decision axis" test |
| Primary tag | Separate `primary_tag` field in schema |
| Tag nodes shown | Only primary_tags appearing on 2+ records |
| Tag node style | Hollow ring, muted color |
| Tag↔record edges | Gray, solid |
| Within-project edges | Dark muted project color, solid |
| Cross-project edges | Gold, dashed |
| Supersedes edges | Red, dashed (unchanged) |
| Tag proposal flow | Instruction-based (hook prompt reads tags.yml) |
| Cross-link discovery | Hybrid: auto-suggest + explicit command, chat-based approval |
| Filter sidebar | Tag node toggle added |

## Dependency Graph

```
Task 1 (Tag Registry)
  ├──→ Task 2 (Schema Update)
  │      └──→ Task 3 (Record Normalization)
  │             ├──→ Task 4 (Hook Prompt Update)
  │             ├──→ Task 5 (Visualization Update)
  │             └──→ Task 6 (Cross-Link Discovery)
  └──→ Task 4 (Hook Prompt Update)
```

---

### Task 1: Create Tag Registry
**Status:** done
**Estimate:** medium (~30k tokens)
**Dependencies:** none
**Acceptance criteria:**
- File `~/.claude/decisions/tags.yml` exists
- Contains 15-25 tags, each with name, axis, description
- Every unique tag from existing 28 records maps to exactly one registry entry (merged where overlapping)
- No two tags share the same axis description (distinctness test passes)
- Existing raw tags: architecture, codegen, agent-isolation, merge, error-handling, resilience, frontend, component-library, manifest, deterministic, ui-design, migration, multi-agent, mvp-generation, orchestration, layout, model-selection, cost, data-quality, ontology, investigator, database, sqlite, environment, ntid, identity, hooks, global-scope, quality-gate, recall, installer, distribution, innersource, project-detection, git, project-context, decision-memory, knowledge-graph, ux, schema, format, simplicity, graph, relationships, id-scheme, record-types, taxonomy, storage, central-store, testing, incremental, visualization, ui
**Steps:**
- [x] Read all 28 decision records and extract full tag list
- [x] Group tags by semantic similarity, identify overlaps
- [x] Apply "distinct decision axis" rule to merge or keep tags
- [x] Write `~/.claude/decisions/tags.yml` with final registry
- [x] Verify tag count is 15-25 and each has unique axis

---

### Task 2: Schema Update
**Status:** done
**Estimate:** medium (~25k tokens)
**Dependencies:** Task 1
**Acceptance criteria:**
- `decision-engine.py` has `primary_tag` column in decisions table schema
- Indexer reads `primary_tag` from frontmatter and stores it
- `lib/frontmatter.py` parses `primary_tag` field correctly
- Running `decision-engine.py index` with a record containing `primary_tag` stores it in DB
- Existing records without `primary_tag` don't crash the indexer (graceful fallback)
**Steps:**
- [x] Add `primary_tag TEXT` column to decisions table in `decision-engine.py`
- [x] Update `index_records()` to extract and store `primary_tag` from frontmatter
- [x] Update `lib/frontmatter.py` if needed to handle new field
- [x] Test: run `decision-engine.py index` — no errors with current records (no primary_tag yet)
- [x] Verify DB schema has new column after index

---

### Task 3: Record Normalization
**Status:** done
**Estimate:** large (~60k tokens)
**Dependencies:** Task 1, Task 2
**Acceptance criteria:**
- All 28 records have `primary_tag` field set to a valid registry tag
- All tags in each record exist in `tags.yml`
- No duplicate/overlapping tags per the axis rule within a single record
- Changes are presented to user for review before writing
- After normalization, `decision-engine.py index` runs cleanly
**Steps:**
- [x] Read tags.yml registry and all 28 records
- [x] For each record: map existing tags to registry tags, pick primary_tag
- [x] Compile full change list (old tags → new tags + primary_tag for each record)
- [x] Present changes to user in chat for approval
- [x] Write approved changes to all record files
- [x] Run `decision-engine.py index` and verify clean indexing

---

### Task 4: Hook Prompt Update
**Status:** done
**Estimate:** small (~15k tokens)
**Dependencies:** Task 1, Task 3
**Acceptance criteria:**
- `~/.claude/hooks/frontier-brain/decision-detect.js` injects instruction to read `tags.yml`
- Prompt instructs Claude to: check registry, propose new tags with rationale if needed, always set `primary_tag`
- Prompt includes path to tags.yml
- Hook still fires correctly on user prompt submit
**Steps:**
- [x] Read current `decision-detect.js` hook
- [x] Add tag registry instructions to the injected prompt text
- [x] Include `primary_tag` requirement in recording instructions
- [x] Verify hook syntax is valid (no JS errors)

---

### Task 5: Visualization Update
**Status:** done
**Estimate:** large (~80k tokens)
**Dependencies:** Task 2, Task 3
**Acceptance criteria:**
- Tag nodes rendered as hollow rings with muted color
- Only primary_tags appearing on 2+ records get nodes
- Tag↔record edges are gray, solid
- Within-project record↔record edges use dark muted project color, solid
- Cross-project record↔record edges are gold (#FFD700), dashed
- Supersedes edges unchanged (red, dashed)
- Legend updated with all new element types
- Filter sidebar has "Tag nodes" toggle that hides/shows tag nodes + their edges
- Graph renders without errors with current data
**Steps:**
- [x] Read current `visualize.py` to understand rendering structure
- [x] Add tag node data generation (query primary_tags with 2+ records)
- [x] Add tag node rendering (hollow ring SVG, muted color, smaller radius)
- [x] Add tag↔record edge rendering (gray, solid)
- [x] Change within-project edges to dark muted project color
- [x] Add cross-project edge detection and gold dashed rendering
- [x] Update legend panel with new elements
- [x] Add "Tag nodes" toggle to filter sidebar
- [x] Generate graph and verify visual output

---

### Task 6: Cross-Link Discovery
**Status:** done
**Estimate:** medium (~35k tokens)
**Dependencies:** Task 1, Task 3
**Acceptance criteria:**
- `decision-engine.py cross-link` command exists and runs
- Algorithm scores candidates by: shared tags (weighted) + title/body text similarity
- Only surfaces cross-project pairs (same-project pairs excluded)
- Output: JSON array of candidates with source_id, target_id, score, rationale
- Auto-suggest logic: after recording, if cross-project match found, prints suggestion
**Steps:**
- [x] Add `cross-link` subcommand to decision-engine.py CLI
- [x] Implement tag overlap scoring (shared tags between records of different projects)
- [x] Implement text similarity scoring (TF-IDF or keyword overlap on title+body)
- [x] Combine scores, rank candidates above threshold
- [x] Output ranked candidates as JSON with rationale strings
- [x] Add auto-suggest function callable after a new record is indexed
- [x] Test with current 28 records — verify output format
