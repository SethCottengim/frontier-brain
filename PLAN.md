# frontier-brain Installer Redesign — Plan

## Goal

Distribute frontier-brain to 1000s of LM employees via InnerSource catalog. Users clone repo, run `bash install.sh`, update via `git pull && bash install.sh`. Idempotent, safe upgrades, clean uninstall. Zero external dependencies (Python stdlib only).

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Audience | 1000s of LM employees via InnerSource |
| 2 | Distribution | `git clone` → `bash install.sh` → `git pull && bash install.sh` |
| 3 | Settings.json | Surgical merge, keyed on `decision-detect` in command string |
| 4 | Skills management | Manifest-based — only touch frontier-brain's own files |
| 5 | Skills in repo | All 4: decision-recall, decision-record, decision-harvest, open-brain |
| 6 | Version tracking | Git commit hash stored in manifest |
| 7 | Uninstall | `bash install.sh uninstall` — removes all managed files, preserves decisions/ |
| 8 | Output | Smart — compact on success, verbose on failure |
| 9 | Prerequisites | Hard fail if Python < 3.11 |
| 10 | Node dependency | Eliminate — rewrite hook in Python |
| 11 | PyYAML dependency | Eliminate — stdlib-only frontmatter parser |
| 12 | Installer language | Python (`installer/main.py`) with 3-line bash wrapper |
| 13 | Reindex on install | Always run `decision-engine.py index` |
| 14 | Settings backup | `settings.json.bak-frontier-brain` before modification |
| 15 | Force flag | `--force` to reinstall same commit |

## Repo Layout (After)

```
frontier-brain/
├── install.sh                          # 3-line bash wrapper
├── installer/
│   └── main.py                         # all install/uninstall logic
├── bin/
│   ├── decision-engine.py              # updated: no yaml import
│   ├── visualize.py
│   └── static/
│       ├── d3.v7.min.js
│       └── index.html
├── lib/
│   ├── graphdb.py
│   ├── router.py
│   └── frontmatter.py                  # NEW: stdlib yaml-subset parser
├── hooks/
│   └── decision-detect.py              # CHANGED: was .js, now .py
├── .claude/
│   └── skills/
│       ├── decision-recall/SKILL.md
│       ├── decision-record/SKILL.md
│       ├── decision-harvest/SKILL.md   # NEW in repo (was only in ~/.claude)
│       └── open-brain/SKILL.md         # NEW in repo (was only in ~/.claude)
├── decisions/
│   ├── TEMPLATE.md
│   └── SCHEMA.md
├── CLAUDE.md
└── PLAN.md
```

## Installed Layout

```
~/.claude/
├── decisions/                          # user data — NEVER touched by uninstall
│   ├── *.md                            # decision records
│   ├── brain.db                        # rebuilt on every install
│   └── graph.html                      # generated viz
├── frontier-brain/
│   ├── .manifest                       # JSON: commit, timestamp, file list
│   ├── bin/
│   │   ├── decision-engine.py
│   │   ├── visualize.py
│   │   └── static/{d3.v7.min.js, index.html}
│   └── lib/
│       ├── graphdb.py
│       ├── router.py
│       └── frontmatter.py
├── hooks/
│   └── frontier-brain/
│       └── decision-detect.py
├── skills/
│   ├── decision-recall/SKILL.md
│   ├── decision-record/SKILL.md
│   ├── decision-harvest/SKILL.md
│   └── open-brain/SKILL.md
└── settings.json                       # hook entry surgically merged
```

## Manifest Schema

```json
{
  "commit": "abc1234def5678...",
  "installed_at": "2026-04-28T14:30:00Z",
  "files": [
    "~/.claude/frontier-brain/bin/decision-engine.py",
    "~/.claude/frontier-brain/bin/visualize.py",
    "~/.claude/frontier-brain/bin/static/d3.v7.min.js",
    "~/.claude/frontier-brain/bin/static/index.html",
    "~/.claude/frontier-brain/lib/graphdb.py",
    "~/.claude/frontier-brain/lib/router.py",
    "~/.claude/frontier-brain/lib/frontmatter.py",
    "~/.claude/hooks/frontier-brain/decision-detect.py",
    "~/.claude/skills/decision-recall/SKILL.md",
    "~/.claude/skills/decision-record/SKILL.md",
    "~/.claude/skills/decision-harvest/SKILL.md",
    "~/.claude/skills/open-brain/SKILL.md"
  ]
}
```

## Tasks

### Dependency Graph

```
Task 1 (repo restructure)  ──┐
Task 2 (eliminate pyyaml)  ───┤
Task 3 (hook → python)    ───┼──→ Task 4 (installer) → Task 5 (bash wrapper) → Task 7 (test)
Task 6 (manifest design)  ───┘
```

Tasks 1-3, 6 are independent. Task 4 depends on all. Task 5 trivial. Task 7 validates.

---

### Task 1: Repo Restructure — Move Skills Into Repo

**Status:** not started
**Estimate:** small (~5k tokens)

- [ ] Copy `~/.claude/skills/decision-harvest/SKILL.md` → repo `.claude/skills/decision-harvest/SKILL.md`
- [ ] Copy `~/.claude/skills/open-brain/SKILL.md` → repo `.claude/skills/open-brain/SKILL.md`
- [ ] Verify all 4 skills present in repo `.claude/skills/`
- [ ] Remove stale `decisions/` dir from repo (TEMPLATE.md, SCHEMA.md go to `docs/` or root)

---

### Task 2: Eliminate PyYAML Dependency

**Status:** not started
**Estimate:** medium (~20k tokens)

- [ ] Create `lib/frontmatter.py` — parse `---` fenced YAML frontmatter
  - Handle: strings, integers, dates (YYYY-MM-DD), lists (`[a, b]` and `- item`), empty values
  - Return: `(metadata_dict, body_string)`
  - No nested objects, no anchors, no multi-line strings — flat only
- [ ] Update `bin/decision-engine.py`: replace `import yaml` with `from lib.frontmatter import parse`
  - Fix all `yaml.safe_load()` calls to use new parser
- [ ] Test against every existing record in `~/.claude/decisions/*.md`
  - Parse with both old (yaml) and new (frontmatter.py), diff outputs
  - Zero differences = pass

---

### Task 3: Rewrite Hook in Python

**Status:** not started
**Estimate:** small (~10k tokens)

- [ ] Create `hooks/decision-detect.py` — same behavior as current `.js`:
  - Read JSON from stdin
  - Detect project via `git remote get-url origin` (fallback: basename of cwd)
  - Detect user via `$USER` env var
  - Output `hookSpecificOutput` JSON to stdout
- [ ] Remove `hooks/decision-detect.js`
- [ ] Update `.claude/settings.json` in repo to reference `.py` not `.js`
- [ ] Test: pipe sample hook input JSON → verify output matches expected format

---

### Task 4: Build Installer (`installer/main.py`)

**Status:** not started
**Estimate:** large — decomposed into subtasks below

This is the core work. ~300-400 lines of Python. Broken into 5 subtasks.

#### Task 4a: Prereq Checks + CLI Arg Parsing

**Estimate:** ~10k tokens

- [ ] Parse args: `install` (default), `uninstall`, `--force`
- [ ] `check_prereqs()`: verify Python >= 3.11, print actionable error if not
- [ ] Detect repo root (script's parent dir)
- [ ] Detect git commit hash via `git rev-parse HEAD`

#### Task 4b: Manifest — Load, Build, Diff

**Estimate:** ~15k tokens

- [ ] `load_manifest(path)` — read `~/.claude/frontier-brain/.manifest` or return `{"commit": None, "files": []}`
- [ ] `build_manifest(repo_root)` — scan repo, produce source→target path mapping + commit hash
  - Hardcoded mapping: `bin/*` → `~/.claude/frontier-brain/bin/*`, `lib/*` → `~/.claude/frontier-brain/lib/*`, etc.
  - Skills: `.claude/skills/*/SKILL.md` → `~/.claude/skills/*/SKILL.md`
  - Hook: `hooks/decision-detect.py` → `~/.claude/hooks/frontier-brain/decision-detect.py`
- [ ] `diff_manifests(old, new)` — return `{added: [], updated: [], removed: [], unchanged: []}`

#### Task 4c: File Operations — Install, Cleanup, Reindex

**Estimate:** ~15k tokens

- [ ] `install_files(file_map)` — mkdir -p parents, copy files, return counts
- [ ] `cleanup_stale(removed_files)` — delete files in old manifest but not in new, remove empty parent dirs
- [ ] `reindex_db()` — subprocess call to `decision-engine.py index`
- [ ] `save_manifest(path, manifest)` — write new manifest JSON

#### Task 4d: Settings.json — Surgical Merge

**Estimate:** ~20k tokens

- [ ] `backup_settings(path)` — copy to `settings.json.bak-frontier-brain`
- [ ] `merge_hook(settings_path, hook_command)`:
  - Load JSON
  - Find existing frontier-brain hook entry (search for `decision-detect` in command strings)
  - If found: update command in place (handles .js→.py migration, timeout changes)
  - If not found: append new entry to `UserPromptSubmit` hooks array
  - If `UserPromptSubmit` key missing: create it
  - Write JSON back (preserve formatting with `indent=2`)
- [ ] `remove_hook(settings_path)` — find and remove frontier-brain hook entry, clean up empty arrays

#### Task 4e: Uninstall + Smart Output

**Estimate:** ~15k tokens

- [ ] `uninstall()`:
  - Load manifest
  - Delete all listed files
  - Remove hook from settings.json
  - Delete manifest file
  - Remove empty dirs (`frontier-brain/bin/`, `frontier-brain/lib/`, etc.)
  - Print: "Uninstalled. Your decisions in ~/.claude/decisions/ were preserved."
- [ ] `print_summary(mode, counts)`:
  - Fresh install: file count, skill count, hook status, brain.db record count
  - Upgrade: files updated/added/removed, skills changed, hook status
  - Up to date: one line + hint about `--force`
  - Error: full detail + suggested fix

---

### Task 5: Bash Wrapper

**Status:** not started
**Estimate:** trivial (~2k tokens)

- [ ] Rewrite `install.sh`:
  ```bash
  #!/usr/bin/env bash
  command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required. Install Python 3.11+."; exit 1; }
  exec python3 "$(dirname "$0")/installer/main.py" "$@"
  ```
- [ ] Delete old `install.sh` content

---

### Task 6: Manifest Schema (Design Only)

**Status:** done (defined above in this plan)
**Estimate:** 0 — already specified

---

### Task 7: End-to-End Testing

**Status:** not started
**Estimate:** medium (~20k tokens)

Test scenarios (manual or scripted):

- [ ] **Fresh install** on empty `~/.claude/` — all files created, hook registered, brain.db initialized, manifest written
- [ ] **Upgrade from legacy** (no manifest exists) — treats as fresh install, old .js hook replaced with .py
- [ ] **Upgrade from v2** (manifest exists, different commit) — files updated, stale files removed, manifest updated
- [ ] **Same version** — prints "already up to date", exits 0
- [ ] **Same version + `--force`** — reinstalls everything
- [ ] **Uninstall** — all managed files removed, hook removed from settings.json, `~/.claude/decisions/` preserved, manifest deleted
- [ ] **Uninstall when not installed** — graceful error message
- [ ] **Prereq failure** — Python 3.10 → clear error message (test with version mock if needed)
- [ ] **Corrupted settings.json** — graceful error, no data loss (backup exists)

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| settings.json corruption on merge | User loses Claude Code config | Backup before modify, atomic write |
| Stale .js hook after upgrade | Duplicate hooks fire | Installer finds by `decision-detect` substring, replaces regardless of extension |
| Permission denied on `~/.claude/` | Install fails | Clear error message with chmod suggestion |
| No git repo (downloaded zip) | `git rev-parse HEAD` fails | Fallback to "unknown" commit, warn user, still install |
| Skills dir doesn't exist | First-time Claude Code user | `mkdir -p` before copying |
