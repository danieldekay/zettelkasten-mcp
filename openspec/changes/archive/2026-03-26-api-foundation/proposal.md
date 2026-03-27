# Proposal: API Foundation — JSON Responses, FTS5 Search & Metadata Exposure

## Why

Three critical implementation gaps discovered during the 2026-03 knowledge
management research sprint block reliable agent-driven workflows:

1. **All 14 MCP tools return plain text** — AI agents must parse natural language
   to extract note IDs, link counts, and status fields. This is the root cause of
   hallucination and parsing failures in every agent workflow that reads from
   the server.

2. **FTS5 full-text search table exists but is never queried** — `zk_search_notes`
   performs a Python-side linear scan of all note content (O(n)), bypassing the
   `notes_fts` SQLite FTS5 virtual table that is created on every `zk_rebuild_index`
   call. At 1 000+ notes the degradation is measurable; at 5 000+ notes it is
   severely user-visible.

3. **The `metadata` field on `Note` is invisible via the API** — the data model
   includes a `metadata: dict[str, Any]` field that stores arbitrary key-value
   pairs (source URL, ISBN, reading status, priority flags), but no MCP tool
   exposes this field for reading or writing. The field exists only in the
   Markdown frontmatter and the DB, completely bypassing every agent workflow.

These three gaps are pre-conditions for all subsequent phases. Adding batch
operations (Phase 2) on top of a plain-text API compounds the fragility. Fixing
the API surface now minimises rework.

## What Changes

### New Capabilities
- `json-responses` — All 14 existing MCP tools return a structured dict/JSON
  payload in addition to (or instead of) their current plain-text string. Each
  tool has a defined response schema documented in its spec.
- `fts5-search` — `zk_search_notes` is rewritten to query the `notes_fts` FTS5
  virtual table with BM25 relevance ranking. The Python-side linear scan is
  removed.
- `metadata-access` — `zk_create_note` and `zk_update_note` accept an optional
  `metadata` parameter (JSON string or dict). `zk_get_note` includes the
  `metadata` dict in its response.

### Modified Capabilities
- `note-crud` — Response schema updated to include structured fields; metadata
  read/write added to create/update/get operations.
- `search` — Query engine replaced from Python linear scan to FTS5; response
  schema updated.

## Impact

- **`mcp_server.py`** — all 14 tool handlers updated to return structured responses
- **`zettel_service.py`** — `search_notes` delegates to FTS5; `create_note` /
  `update_note` / `get_note` accept and return metadata
- **`note_repository.py`** — `search` method rewritten to use FTS5; `create` /
  `update` / `get` methods updated for metadata
- **`schema.py`** — no model changes required (metadata field already exists)
- **Tests** — all existing tests updated for new response format; new tests for
  FTS5 correctness and metadata round-trip
- **README** — tool reference table updated with new response schemas

## Success Criteria

- Zero tools return bare plain-text strings as their primary response
- `zk_search_notes` query time < 50 ms for 10 000 notes (vs. current O(n) scan)
- `zk_search_notes` returns BM25-ranked results (most relevant first)
- `zk_get_note` includes a `metadata` key in its response dict
- `zk_create_note` and `zk_update_note` accept a `metadata` parameter
- All 80+ existing tests pass with updated response assertions
- `ruff check` and `ruff format` report zero violations
