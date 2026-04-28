# Record Schema

## Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | yes | Global sequential integer (1, 2, 3, ...) |
| `title` | string | yes | Short descriptive title |
| `type` | enum | yes | `decision` \| `knowledge` \| `context` |
| `status` | enum | yes | `active` \| `superseded` \| `deprecated` |
| `date` | date | yes | ISO 8601 date (YYYY-MM-DD) when recorded |
| `project` | string | yes | Project scope (e.g., `sempl-core/agents`, `frontier-brain`) |
| `tags` | list[string] | yes | Topic tags for search (lowercase, hyphenated) |
| `affects` | list[string] | no | Paths affected by this record (default `[]`) |
| `recorded_by` | string | yes | NTID of person who recorded |
| `supersedes` | list[integer] | no | Record IDs this entry replaces |
| `related` | list[integer] | no | Record IDs topically connected |

## Record Types

| Type | What | Example |
|------|------|---------|
| `context` | Project purpose, goals, constraints | "SEMPL automates ISO 15288 via staged agent pipelines" |
| `decision` | Choice between alternatives + rationale | "Strands over LangChain — lighter, native Bedrock" |
| `knowledge` | Validated fact learned through experience | "Unset VPC endpoint env var locally or Bedrock calls fail" |

## Status Values

| Status | Meaning |
|--------|---------|
| `active` | Current and in effect |
| `superseded` | Replaced by a newer record (check `superseded_by` relations) |
| `deprecated` | No longer relevant, not replaced |

## Relationship Types

| Relation | Meaning | Auto-Inverse |
|----------|---------|-------------|
| `supersedes` | Replaces an older record | `superseded_by` (auto-created) |
| `related` | Topically connected (bidirectional) | `related` (mirrored) |

Only two relationship types. `supersedes` is directional with auto-inverse. `related` is bidirectional.

## Body

Free-text, 2-5 sentences. No mandatory sections. Captures what was chosen/learned and why.

## Conventions

- IDs are global sequential integers starting at 1
- Filename format: `NNN-slug.md` (zero-padded 3 digits, e.g., `001-sempl-context.md`)
- Tags: lowercase, hyphenated (e.g., `agent-framework`, `state-management`)
- One record per file
- `supersedes` in frontmatter triggers auto-creation of inverse `superseded_by` relation in graph
- `related` in frontmatter triggers bidirectional `related` relation in graph
- Project identified by git remote URL (extract repo name) or directory basename as fallback
- Storage location: `~/.claude/decisions/` (central, survives project clones/deletes)
