# Tasks: API Foundation

Resolves: JSON responses, FTS5 search, metadata access

## 1. Structured JSON Responses

- [x] 1.1 Define a `ToolResponse` TypedDict or dataclass with `summary: str` as a shared base in `mcp_server.py`
- [x] 1.2 Update `zk_create_note` to return `{"note_id", "file_path", "summary"}`
- [x] 1.3 Update `zk_get_note` to return `{"note_id", "title", "note_type", "tags", "links", "created_at", "updated_at", "content", "metadata", "summary"}`
- [x] 1.4 Update `zk_update_note` to return `{"note_id", "updated_fields", "summary"}`
- [x] 1.5 Update `zk_delete_note` to return `{"note_id", "deleted", "summary"}`
- [x] 1.6 Update `zk_create_link` to return `{"source_id", "target_id", "link_type", "summary"}`
- [x] 1.7 Update `zk_remove_link` to return `{"source_id", "target_id", "removed", "summary"}`
- [x] 1.8 Update `zk_get_linked_notes` to return `{"note_id", "direction", "notes": [...], "total", "summary"}`
- [x] 1.9 Update `zk_search_notes` to return `{"notes": [...], "total", "query", "summary"}`
- [x] 1.10 Update `zk_find_similar_notes` to return `{"notes": [...], "total", "summary"}`
- [x] 1.11 Update `zk_find_central_notes` to return `{"notes": [...], "total", "summary"}`
- [x] 1.12 Update `zk_find_orphaned_notes` to return `{"notes": [...], "total", "summary"}`
- [x] 1.13 Update `zk_get_all_tags` to return `{"tags": [{"name": str, "count": int}], "total", "summary"}`
- [x] 1.14 Update `zk_list_notes_by_date` to return `{"notes": [...], "total", "summary"}`
- [x] 1.15 Update `zk_rebuild_index` to return `{"notes_indexed", "errors": [...], "summary"}`
- [x] 1.16 Add structured error response `{"error": true, "error_type", "message", "summary"}` to all error paths

## 2. FTS5 Full-Text Search

- [x] 2.1 Update `NoteRepository.search()` — add FTS5 branch: when `query` is provided, use `SELECT ... FROM notes n JOIN notes_fts f ON n.id = f.note_id WHERE notes_fts MATCH :q ORDER BY rank LIMIT :limit`
- [x] 2.2 Combine FTS5 results with tag/note_type SQL predicates in the same query
- [x] 2.3 Remove Python-side content filtering loop from `NoteRepository.search()`
- [x] 2.4 Update `NoteRepository.create()` — insert into `notes_fts` in same transaction as `notes` insert
- [x] 2.5 Update `NoteRepository.update()` — update `notes_fts` row in same transaction
- [x] 2.6 Update `NoteRepository.delete()` — delete from `notes_fts` in same transaction
- [x] 2.7 Write tests: keyword search returns FTS5 results ranked by relevance
- [x] 2.8 Write tests: filter-only search (no query) does not use FTS5 join
- [x] 2.9 Write tests: combined query + tag + note_type filter returns correct intersection
- [x] 2.10 Write tests: FTS5 stays in sync after create / update / delete operations
- [ ] 2.11 Write performance test: 10 000 notes, search returns in < 50 ms *(not implemented — FTS5 index provides BM25 ranking; performance is structurally sound but the 50 ms assertion was not written. Deferred.)*

## 3. Metadata Access

- [x] 3.1 Update `ZettelService.create_note()` — accept `metadata: str | dict | None` parameter; parse JSON string if str
- [x] 3.2 Update `ZettelService.update_note()` — accept `metadata: str | dict | None` parameter
- [x] 3.3 Update `ZettelService.get_note()` — include `metadata` dict in returned Note representation
- [x] 3.4 Update `NoteRepository.create()` — persist metadata to `notes.metadata` column (JSON-serialised)
- [x] 3.5 Update `NoteRepository.update()` — persist metadata update
- [x] 3.6 Update `NoteRepository.get()` — deserialise `metadata` JSON from DB into dict
- [x] 3.7 Update `zk_create_note` tool signature — add `metadata: str` optional parameter with docstring
- [x] 3.8 Update `zk_update_note` tool signature — add `metadata: str` optional parameter
- [x] 3.9 Write tests: create → get metadata round-trip with various value types (str, int, list, nested dict)
- [x] 3.10 Write tests: invalid JSON metadata returns structured error, no note persisted
- [x] 3.11 Write tests: get note with no metadata returns `"metadata": {}`

## 4. Housekeeping

- [x] 4.1 Update all existing test assertions to expect dict responses instead of string responses
- [x] 4.2 Update README tool reference table with new response schemas for all 14 tools
- [x] 4.3 Run full test suite — all tests must pass
- [x] 4.4 Run `ruff format` and `ruff check` — zero violations
- [x] 4.5 Run `mypy src/` — no new type errors
