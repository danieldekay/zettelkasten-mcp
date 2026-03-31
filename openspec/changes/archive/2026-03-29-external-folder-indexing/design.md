## Context

The Zettelkasten MCP server currently manages a single writable notes directory (`ZETTELKASTEN_NOTES_DIR`) and a SQLite index (`ZETTELKASTEN_DATABASE_PATH`). Users frequently maintain Markdown files outside that directory — project documentation, reference material, book notes, exported content — that they want to link from their Zettelkasten without moving or duplicating those files.

The current architecture stores notes in Markdown with YAML frontmatter and indexes them in SQLite. The `NoteRepository` handles both filesystem writes and DB indexing. The `ZettelkastenConfig` (Pydantic model, env-var backed) is the single source of truth for runtime configuration.

## Goals / Non-Goals

**Goals:**
- Allow one or more external directories to be registered as read-only "watch folders" via config.
- On server startup, scan watch folders and ingest compatible Markdown files into the SQLite index with a `is_readonly=True` flag and their original `source_path`.
- Make watch-folder notes searchable and traversable via the same graph/search tools as primary notes.
- Prevent MCP mutation tools (`zk_update_note`, `zk_delete_note`) from modifying read-only notes.
- Expose a `zk_sync_watch_folders` tool to re-scan without restarting the server.
- Support frontmatter-compatible files (with at least `title` or `id`) as full notes, and frontmatter-absent files as lightweight document stubs with auto-generated IDs.

**Non-Goals:**
- Bi-directional sync (writing back changes to watch-folder files).
- File-system watching / inotify-based live updates (polling on demand is sufficient for v1).
- Moving or copying watch-folder files into the primary notes directory.
- Conflict resolution for duplicate IDs across notes and watch folders (ID namespacing deferred).
- Watch-folder support on remote/network filesystems.

## Decisions

### Decision 1: Read-only flag in the DB model, not a separate table

**Choice:** Add `is_readonly BOOLEAN` and `source_path TEXT` columns to the existing `notes` table rather than a new `external_notes` table.

**Rationale:** Keeps search, graph traversal, and link resolution uniform — all existing queries work without modification. A separate table would require JOIN-based unions in every query path. The trade-off is a modest schema migration, but that is already handled by the rebuild-from-markdown approach (the DB is always a disposable index).

**Alternative considered:** Separate `external_notes` table. Rejected because it doubles query surface area and breaks existing `NoteRepository.search()` without deep refactoring.

### Decision 2: Config as a comma-separated env var (`ZETTELKASTEN_WATCH_DIRS`)

**Choice:** Parse `ZETTELKASTEN_WATCH_DIRS` as a colon- or comma-separated list of absolute paths, stored as `list[Path]` on `ZettelkastenConfig`.

**Rationale:** Consistent with the existing env-var-backed Pydantic config pattern. Easy to set in Claude Desktop's `mcpServers` config JSON. Supports zero watch dirs (empty string / unset = disabled).

**Alternative considered:** A separate JSON config file listing watch dirs. Rejected to avoid introducing a new config format alongside the existing env-var approach.

### Decision 3: Ingestion on startup + on-demand sync tool

**Choice:** Run watch-folder indexing once at startup (after primary notes indexing) and expose `zk_sync_watch_folders` for subsequent re-scans.

**Rationale:** Startup indexing ensures the graph is complete immediately. On-demand sync avoids filesystem polling overhead during normal operation. A future enhancement can add periodic background polling if needed.

**Alternative considered:** File-system event watching (e.g., `watchdog` library). Rejected for v1 due to added dependency and complexity; the use case is read-heavy, not write-heavy.

### Decision 4: Auto-generate IDs for frontmatter-absent files

**Choice:** For Markdown files with no `id` in frontmatter, generate a deterministic ID from the file's absolute path hash (e.g., `ext-<sha256[:12]>`). For files with a frontmatter `id`, use that directly.

**Rationale:** Stable IDs across re-scans (prevents orphaned links). The `ext-` prefix namespaces external notes, making it easy to identify their origin and avoid collisions with timestamp-based primary note IDs.

**Alternative considered:** Use filename as ID. Rejected because filenames can collide across directories and change on rename.

### Decision 5: Mutation guard at the service layer

**Choice:** `ZettelService.update_note()` and `ZettelService.delete_note()` check `note.is_readonly` before proceeding, raising a `PermissionError` with a clear message.

**Rationale:** Centralising the guard in the service layer (not the MCP server handler) ensures it applies regardless of how the service is called, and keeps MCP handlers thin.

## Risks / Trade-offs

- **Schema migration**: Adding columns to `notes` requires a DB migration. Mitigated by the existing pattern of auto-rebuilding the SQLite index from Markdown on startup — the DB is treated as disposable, so a fresh init handles the new columns automatically.
- **Large watch folders**: Scanning thousands of files on startup could slow server boot. Mitigated by logging progress and limiting initial implementation to synchronous scan (async optimisation deferred to a follow-up). A configurable depth limit (`ZETTELKASTEN_WATCH_MAX_DEPTH`) can be added if needed.
- **ID collisions**: If a watch-folder file declares an `id` already used by a primary note, the last-written entry wins. Mitigated by the `ext-` prefix for auto-generated IDs, and a warning log when a collision is detected.
- **Frontmatter parsing errors**: Malformed YAML frontmatter in watch files should not crash startup. Mitigated by catching parse errors per-file and logging a warning before continuing.

## Migration Plan

1. Add `is_readonly` and `source_path` columns to `DBNote` model.
2. Delete existing `data/db/zettelkasten.db` (or allow auto-rebuild on startup to recreate schema).
3. Set `ZETTELKASTEN_WATCH_DIRS` in env / Claude Desktop config.
4. Restart server — watch folders are indexed on startup.
5. **Rollback**: Unset `ZETTELKASTEN_WATCH_DIRS`, restart. Watch-folder rows in the DB are harmless if present; re-deleting the DB restores a clean state.

## Open Questions

- Should `zk_sync_watch_folders` do a full re-scan (drop + re-insert all watch-folder rows) or an incremental diff based on file mtime? Full re-scan is simpler for v1 but may be slow for large watch folders.
- Should watch-folder notes appear in `zk_list_notes` by default, or only when explicitly requested (e.g., `include_external=true` parameter)? Default-include keeps the graph complete; default-exclude avoids surprising users with many external files. **Tentative decision**: default-include with a filter option.
- How should `zk_create_note` behave if a link target references a watch-folder note ID? It should be allowed (linking is the primary use case), but the forward-reference must resolve at index time.
