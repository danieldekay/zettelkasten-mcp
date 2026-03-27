# Tasks: Core Enhancements

Resolves: #5, #6, #9, #14

## 1. Batch Note Creation (#5)

- [x] 1.1 Add `NoteRepository.create_batch(notes: list[Note]) -> list[Note]`
- [x] 1.2 Add `ZettelService.create_notes_batch(notes: list[dict]) -> dict`
- [x] 1.3 Register `zk_create_notes_batch` in `mcp_server.py`
- [x] 1.4 Write tests: success, validation failure, DB error rollback
- [x] 1.5 Add performance test: 50-note batch vs 50 individual calls

## 2. Batch Link Creation (#6)

- [x] 2.1 Add `NoteRepository.create_links_batch(links: list[dict]) -> int`
- [x] 2.2 Add `ZettelService.create_links_batch(links: list[dict]) -> dict`
- [x] 2.3 Register `zk_create_links_batch` in `mcp_server.py`
- [x] 2.4 Write tests: success, invalid type, missing target note
- [x] 2.5 Add performance test: 20-link batch vs 20 individual calls

## 3. Note Verification (#9)

- [x] 3.1 Add `ZettelService.verify_note(note_id: str) -> dict`
- [x] 3.2 Register `zk_verify_note` in `mcp_server.py`
- [x] 3.3 Write tests: fully indexed, file-only, not found

## 4. Index Health Dashboard (#14)

- [x] 4.1 Add `ZettelService.get_index_status() -> dict`
- [x] 4.2 Register `zk_get_index_status` in `mcp_server.py`
- [x] 4.3 Write tests: healthy system, orphaned files, stale DB records

## 5. Housekeeping

- [x] 5.1 Update README tool reference table with new tool signatures
- [x] 5.2 Run full test suite — all tests must pass
- [x] 5.3 Run `ruff format` and `ruff check` — zero violations
- [x] 5.4 Close GitHub issues #5, #6, #9, #14 referencing this change
