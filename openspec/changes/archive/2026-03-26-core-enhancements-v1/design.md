# Design: Core Enhancements

## Architecture Overview

All four tools are implemented as new `@mcp.tool()` methods in
`src/zettelkasten_mcp/server/mcp_server.py`, delegating to new methods on
`ZettelService` and `NoteRepository`.

## 1. Batch Note Creation (`zk_create_notes_batch`)

**MCP Server layer** — `mcp_server.py`
```python
@self.mcp.tool()
def zk_create_notes_batch(notes: list[dict]) -> str:
    ...
```

**Service layer** — `ZettelService.create_notes_batch(notes: list[dict]) -> dict`
- Validates all notes before any DB writes (fail-fast)
- Calls `NoteRepository.create_batch(notes: list[Note]) -> list[Note]`
- Returns `{"created": N, "note_ids": [...], "failed": 0, "errors": []}`

**Repository layer** — `NoteRepository.create_batch`
- Writes all Markdown files first (can be rolled back by deleting files)
- Inserts all DB records in one `session.commit()`
- On exception: deletes any written files, re-raises

## 2. Batch Link Creation (`zk_create_links_batch`)

**Service layer** — `ZettelService.create_links_batch(links: list[dict]) -> dict`
- Validates all link types and note IDs up front
- Calls `NoteRepository.create_links_batch(source_id, links)`
- Single transaction via SQLAlchemy session

**Repository layer** — `NoteRepository.create_links_batch`
- Appends all `DBLink` objects, commits once
- Returns count of created links

## 3. Note Verification (`zk_verify_note`)

**Service layer** — `ZettelService.verify_note(note_id: str) -> dict`
- Checks `Path(notes_dir / f"{note_id}.md").exists()`
- Queries DB for note existence and counts joins on `note_tags` and `links`
- Returns structured dict (no writes)

## 4. Index Health Dashboard (`zk_get_index_status`)

**Service layer** — `ZettelService.get_index_status() -> dict`
- `filesystem_ids = {p.stem for p in notes_dir.glob("*.md")}`
- `db_ids = {row.id for row in session.execute(select(DBNote.id))}`
- Computes set differences for orphaned files / stale DB records
- Reads DB file size via `os.path.getsize(db_path)`

## Error Handling

All batch tools return structured JSON on partial failures rather than raising,
so the MCP client can inspect `errors[]` without an exception.

## Testing Strategy

- Add `tests/test_batch_operations.py` covering all scenarios in the spec
- Add parametrized fixture generating 50-note batches for performance baseline
- Use existing `note_repository` fixture from `conftest.py`
