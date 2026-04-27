# ADR Schema

## Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier, format `ADR-XXX` (zero-padded 3 digits) |
| `title` | string | yes | Short descriptive title |
| `status` | enum | yes | `proposed` \| `accepted` \| `superseded` \| `deprecated` |
| `date` | date | yes | ISO 8601 date (YYYY-MM-DD) when decision was recorded |
| `tags` | list[string] | yes | Topic tags for search (lowercase, hyphenated) |
| `supersedes` | list[string] | no | ADR IDs this decision replaces |
| `related` | list[string] | no | ADR IDs topically connected |
| `project` | string | yes | Project scope (e.g., `frontier-brain`, `sempl-core/agents`) |

## Status Values

| Status | Meaning |
|--------|---------|
| `proposed` | Under consideration, not yet accepted |
| `accepted` | Active decision in effect |
| `superseded` | Replaced by a newer decision (check `superseded_by` relations) |
| `deprecated` | No longer relevant, not replaced |

## Relationship Types

| Relation | Meaning | Auto-Inverse |
|----------|---------|-------------|
| `supersedes` | Replaces an older decision | `superseded_by` |
| `superseded_by` | Was replaced (auto-created) | `supersedes` |
| `related_to` | Topically connected (bidirectional) | `related_to` |
| `informs` | Influenced but didn't replace | `informed_by` |
| `contradicts` | Tension between decisions (bidirectional) | `contradicts` |
| `refines` | Narrows scope of a broader decision | `refined_by` |

## Body Sections

All sections required. Keep concise — ADRs are for recall, not documentation.

- **Context** — Why the decision came up. What problem or question.
- **Considered Options** — Alternatives with pros/cons. Skip if no alternatives existed.
- **Decision** — What was chosen and the primary reason.
- **Consequences** — What changes. Downstream effects.

## Conventions

- IDs are sequential: `ADR-001`, `ADR-002`, etc.
- File names: `ADR-XXX-slug.md` where slug is kebab-case from title
- Tags: lowercase, hyphenated (e.g., `state-management`, `agent-framework`)
- One decision per file
- `supersedes` in frontmatter triggers auto-creation of inverse `superseded_by` relation in graph
- `related` in frontmatter triggers bidirectional `related_to` relation in graph
