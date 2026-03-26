# Tasks: Core Enhancements

Resolves: #5, #6, #9, #14

## 1. Batch Note Creation (#5)

- [ ] 1.1 Add `NoteRepository.create_batch(notes: list[Note]) -> list[Note]`
- [ ] 1.2 Add `ZettelService.create_notes_batch(notes: list[dict]) -> dict`
- [ ] 1.3 Register `zk_create_notes_batch` in `mcp_server.py`
- [ ] 1.4 Write tests: success, validation failure, DB error rollback
- [ ] 1.5 Add performance test: 50-note batch vs 50 individual calls

## 2. Batch Link Creation (#6)

- [ ] 2.1 Add `NoteRepository.create_links_batch(links: list[dict]) -> int`
- [ ] 2.2 Add `ZettelService.create_links_batch(links: list[dict]) -> dict`
- [ ] 2.3 Register `zk_create_links_batch` in `mcp_server.py`
- [ ] 2.4 Write tests: success, invalid type, missing target note
- [ ] 2.5 Add performance test: 20-link batch vs 20 individual calls

## 3. Note Verification (#9)

- [ ] 3.1 Add `ZettelService.verify_note(note_id: str) -> dict`
- [ ] 3.2 Register `zk_verify_note` in `mcp_server.py`
- [ ] 3.3 Write tests: fully indexed, file-only, not found

## 4. Index Health Dashboard (#14)

- [ ] 4.1 Add `ZettelService.get_index_status() -> dict`
- [ ] 4.2 Register `zk_get_index_status` in `mcp_server.py`
- [ ] 4.3 Write tests: healthy system, orphaned files, stale DB records

## 5. Housekeeping

- [ ] 5.1 Update README tool reference table with new tool signatures
- [ ] 5.2 Run full test suite — all tests must pass
- [ ] 5.3 Run `ruff format` and `ruff check` — zero violations
- [ ] 5.4 Close GitHub issues #5, #6, #9, #14 referencing this change
