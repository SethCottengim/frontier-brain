# plan-runner Skill — Plan

## Goal

Build a Claude Code skill (`~/.claude/skills/plan-runner/SKILL.md`) that automates the manual plan-execute loop. User runs `/new-plan` to reach shared understanding, then `/plan-runner` writes a plan file and executes tasks sequentially via fresh sub-agents. Each agent gets clean context, self-verifies, marks completion. Orchestrator tracks progress, handles failures, supports resume.

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Location | `~/.claude/skills/plan-runner/SKILL.md` — global |
| 2 | Trigger | `/plan-runner` slash command + natural language |
| 3 | Plan file | `PLAN-<slug>.md` at directory root, slug auto-generated, kebab-case, max 30 chars |
| 4 | Context transfer | Same conversation as /new-plan — full context available |
| 5 | Task format | Status, Estimate, Dependencies, Acceptance criteria, Steps (checkboxes) |
| 6 | Agent context | Agent reads full PLAN file + CLAUDE.md if present |
| 7 | Task completion | Agent edits plan file: status → done, checks boxes |
| 8 | Execution order | Dependency-aware sequential — one agent at a time |
| 9 | Failure handling | Pause, present failure to user, user decides (fix/retry/skip/abort) |
| 10 | Multiple plans | One pending = use it, multiple pending = ask user, none pending = write new |
| 11 | User comms | Task-level updates: one line start, one line complete per task |
| 12 | Permissions | User chooses agent permission level before execution starts |
| 13 | Verification | Agent self-verifies against acceptance criteria before marking done |
| 14 | Plan-writing | Inline rules in SKILL.md, no agent-skills dependency |
| 15 | /new-plan handoff | Modify /new-plan to offer /plan-runner when interview complete |
| 16 | Task agent prompt | Proven prompt: "Read PLAN file and complete the next task. Mark complete when done." |
| 17 | Implementation | Pure SKILL.md — no external scripts |
| 18 | Plan complete | Summary only: "Plan complete. N/N tasks done." |
| 19 | Cold start | Refuse: "No plan found. Run /new-plan first." |
| 20 | Pre-execution | Pause for review + permission level selection before agents run |
| 21 | State tracking | Grep task metadata between iterations (cheap, no full re-read) |
| 22 | Failed tasks on resume | Ask user: retry or skip |
| 23 | Git | No git commands from agents |

## Task Format (for generated plans)

```markdown
### Task N: Title
**Status:** pending
**Estimate:** small (~Xk tokens)
**Dependencies:** [Task 2, Task 3]  (or "none")
**Acceptance criteria:**
- criterion 1
- criterion 2
**Steps:**
- [ ] step 1
- [ ] step 2
```

## Orchestrator Flow

```
/plan-runner invoked
    │
    ├── PLAN-*.md with pending tasks exists?
    │   ├── One found → resume
    │   ├── Multiple found → ask user which
    │   └── None found ──┐
    │                    │
    │   Conversation context from /new-plan?
    │   ├── Yes → write plan (steps 1+2)
    │   └── No → refuse: "Run /new-plan first"
    │
    ├── Any failed tasks?
    │   └── Ask user: retry or skip each
    │
    ├── Show plan summary
    ├── Ask permission level (default/acceptEdits/auto)
    ├── User confirms "go"
    │
    └── Execution loop:
        ├── Grep task statuses + dependencies
        ├── Find next pending task with all deps done
        │   └── None found → "Plan complete. N/N done."
        ├── Print "▶ Task N/total: Title"
        ├── Spawn agent (reads full PLAN + CLAUDE.md)
        │   ├── Agent completes → "✓ Task N complete"
        │   └── Agent fails → pause, present to user
        └── Loop
```

## Dependency Graph

```
Task 1 (write SKILL.md) → Task 2 (modify /new-plan) → Task 3 (test)
```

Tasks 1-2 are sequential. Task 3 validates everything.

---

### Task 1: Write plan-runner SKILL.md

**Status:** done
**Estimate:** medium (~40k tokens)
**Dependencies:** none
**Acceptance criteria:**
- File exists at `~/.claude/skills/plan-runner/SKILL.md`
- Valid SKILL.md frontmatter (name, description)
- Skill contains all orchestrator logic as natural language instructions
- Covers all flows: new plan, resume, failure, completion
- Plan-writing rules inline (task format, decomposition, 100k limit, 3-10 tasks)
- Task agent prompt template embedded
- Permission level selection before execution
- Grep-based state tracking between iterations
- Task-level update format (▶ start, ✓ complete)
- Cold start refusal when no context and no plan file
- Multiple plan file disambiguation
- Failed task handling on resume (ask retry/skip)
**Steps:**
- [x] Create directory `~/.claude/skills/plan-runner/`
- [x] Write SKILL.md with frontmatter: name `plan-runner`, description covering trigger conditions
- [x] Write Phase 1 instructions: detect existing plans (`ls PLAN-*.md`), determine mode (new/resume)
- [x] Write Phase 2 instructions: plan writing — two-step (write plan, review and decompose oversized tasks), slug generation rules, task format template
- [x] Write Phase 3 instructions: pre-execution review — show summary, ask permission level, wait for user go
- [x] Write Phase 4 instructions: execution loop — grep statuses, find next eligible task, spawn agent, handle result
- [x] Write task agent prompt template: read full PLAN file + CLAUDE.md, complete next pending task, self-verify acceptance criteria, mark done
- [x] Write failure handling instructions: pause, present failure context to user, support retry/skip/abort
- [x] Write completion instructions: summary line when no pending tasks remain
- [x] Write cold start refusal: no plan + no conversation context = refuse with guidance
- [x] Write resume instructions: grep for failed tasks, ask user retry/skip before continuing
- [x] Verify skill is detected by Claude Code (check `ls ~/.claude/skills/plan-runner/`)

---

### Task 2: Modify /new-plan to offer /plan-runner handoff

**Status:** done
**Estimate:** small (~5k tokens)
**Dependencies:** [Task 1]
**Acceptance criteria:**
- `/new-plan` SKILL.md updated with handoff instruction
- When shared understanding reached, /new-plan offers: "Ready to write the plan and execute? Use `/plan-runner`"
- Existing /new-plan behavior unchanged (still interviews, still works standalone)
**Steps:**
- [x] Read current `~/.claude/skills/new-plan/SKILL.md`
- [x] Append handoff instruction: when all questions resolved and shared understanding reached, offer `/plan-runner` as next step
- [x] Verify /new-plan still reads correctly as a standalone skill

---

### Task 3: Manual Validation

**Status:** done
**Estimate:** small (~10k tokens)
**Dependencies:** [Task 1, Task 2]
**Acceptance criteria:**
- `/plan-runner` is listed in Claude Code's available skills
- Invoking `/plan-runner` with no plan file and no context shows refusal message
- SKILL.md is well-formed and parseable
- /new-plan still functions as interview skill
**Steps:**
- [x] Verify `~/.claude/skills/plan-runner/SKILL.md` exists and has valid frontmatter
- [x] Verify `/plan-runner` appears in skill list (check Claude Code recognizes it)
- [x] Read SKILL.md end-to-end and verify all 23 decisions from the plan are encoded
- [x] Verify /new-plan SKILL.md has handoff line and still has original interview instructions
- [x] Check no external dependencies (no Python scripts, no agent-skills references)
