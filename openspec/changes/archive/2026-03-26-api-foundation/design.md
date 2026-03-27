## Context

The `zettelkasten-mcp` server (v1.2.1) exposes 14 MCP tools. All 14 return
human-readable plain-text strings as their sole response. The SQLite index
includes a FTS5 virtual table (`notes_fts`) that is populated by
`zk_rebuild_index` but is never queried — `zk_search_notes` performs a
Python-side linear scan of all in-memory note objects instead. The `Note` model
carries a `metadata: dict[str, Any]` field that is persisted to the Markdown
frontmatter and to the DB, but no MCP tool accepts or returns it.

## Goals / Non-Goals

**Goals:**
- Every MCP tool returns a well-defined JSON-serialisable dict as its primary response
- `zk_search_notes` delegates to the existing FTS5 table; linear scan is removed
- `zk_create_note`, `zk_update_note`, `zk_get_note` accept and expose `metadata`
- No existing tool changes its name, parameter names, or semantic behaviour
- All existing tests continue to pass after assertion updates

**Non-Goals:**
- Adding new tools (belongs to later phases)
- Changing the Markdown frontmatter format
- Streaming or async responses
- Breaking changes to the parameter interface of any existing tool

## Decisions

### D1 — Dual response: structured dict + human summary string

Every tool returns a Python dict with a mandatory `"summary"` key containing the
current plain-text string and additional typed keys for structured data. FastMCP
serialises this as JSON to the MCP client. This avoids breaking any client that
renders `summary` for display while enabling agents to extract `note_id`,
`count`, `notes[]`, etc. without parsing.

```python
# Example: zk_create_note response
{
  "note_id": "20260325T181127281067000",
  "file_path": "/notes/20260325T181127281067000.md",
  "summary": "Note created: 'My Title' (20260325T181127281067000)"
}
```

### D2 — FTS5 query replaces Python scan in `NoteRepository.search`

The `search` method in `NoteRepository` is rewritten to use:

```sql
SELECT n.* FROM notes n
JOIN notes_fts f ON n.id = f.note_id
WHERE notes_fts MATCH :query
ORDER BY rank          -- BM25 rank column from FTS5
LIMIT :limit
```

Tag and `note_type` filters are applied as additional SQL predicates on the main
`notes` table joined to the FTS result. If the query string is empty (tag/type
filter only), the FTS join is skipped and a plain `SELECT` is used (unchanged
behaviour for filter-only queries).

### D3 — `notes_fts` must stay in sync

`NoteRepository.create`, `.update`, and `.delete` each perform a corresponding
`INSERT/UPDATE/DELETE` on `notes_fts` in the same transaction. The existing
full-rebuild path in `zk_rebuild_index` is unchanged as a fallback/recovery
mechanism.

### D4 — Metadata serialised as JSON string in YAML frontmatter

The existing `metadata` key in the Markdown frontmatter is already written as a
YAML mapping. The MCP API accepts metadata as a JSON string parameter (easy for
LLMs to construct) and exposes it as a plain dict in the response. Example
frontmatter:

```yaml
metadata:
  source_url: "https://arxiv.org/abs/2404.16130"
  reading_status: "complete"
```

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Existing tests break on response format change | HIGH | Systematically update all response assertions in a single pass before running the suite |
| FTS5 MATCH syntax differs from Python `in` operator (case-sensitivity, tokenisation) | MEDIUM | Use `UNINDEXED` column for exact-tag filter; FTS only for full-text |
| `notes_fts` out-of-sync after crash mid-write | LOW | Same transaction as note write; rebuild remains available as recovery |
| Metadata JSON parse error from malformed LLM input | MEDIUM | Validate with `json.loads` before persisting; return structured error response |
