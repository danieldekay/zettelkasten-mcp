# Proposal: Core Enhancements

Resolves: #5, #6, #9, #14

## Why

The MCP server's one-note-at-a-time API forces agents to make dozens of sequential
round-trips when ingesting research sessions or meeting transcripts, and provides no
way to check or diagnose the consistency of the underlying storage. These limitations
slow down real workflows and make operational issues hard to detect.

## What Changes

- Add `zk_create_notes_batch` — create up to N notes atomically in a single call
- Add `zk_create_links_batch` — create multiple typed links atomically, rolling back on error
- Add `zk_verify_note` — check whether a specific note is consistent (filesystem + DB in sync)
- Add `zk_get_index_status` — expose a health dashboard for the entire index (counts, orphans, drift)

## Capabilities

### New Capabilities

- `batch-note-creation`: Atomic multi-note creation with per-item error reporting and DB rollback; covers `NoteRepository.create_batch`, `ZettelService.create_notes_batch`, and `zk_create_notes_batch`
- `batch-link-creation`: Atomic multi-link creation with validation and rollback; covers `NoteRepository.create_links_batch`, `ZettelService.create_links_batch`, and `zk_create_links_batch`
- `note-verification`: Single-note consistency check comparing filesystem presence with DB index state; covers `ZettelService.verify_note` and `zk_verify_note`
- `index-health`: Whole-vault index status dashboard exposing note counts, orphaned files, stale DB records, and DB size; covers `ZettelService.get_index_status` and `zk_get_index_status`

### Modified Capabilities

<!-- No existing spec-level requirements changed -->

## Impact

- `src/zettelkasten_mcp/storage/note_repository.py` — two new batch methods
- `src/zettelkasten_mcp/services/zettel_service.py` — four new service methods
- `src/zettelkasten_mcp/server/mcp_server.py` — four new MCP tool registrations
- `README.md` — tool reference table extended
- No breaking changes to existing tools
