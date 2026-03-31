## 1. Data Model & Schema

- [x] 1.1 Add `is_readonly: bool` (default `False`) and `source_path: Optional[str]` (default `None`) columns to `DBNote` in `src/zettelkasten_mcp/models/db_models.py`
- [x] 1.2 Add `is_readonly: bool` (default `False`) and `source_path: Optional[str]` (default `None`) fields to the `Note` Pydantic schema in `src/zettelkasten_mcp/models/schema.py`
- [x] 1.3 Delete `data/db/zettelkasten.db` (or update DB initialisation logic) so the schema is recreated with the new columns on next startup

## 2. Configuration

- [x] 2.1 Add `watch_dirs: list[Path]` field to `ZettelkastenConfig` in `src/zettelkasten_mcp/config.py`, parsed from `ZETTELKASTEN_WATCH_DIRS` (comma-separated env var; defaults to empty list)
- [x] 2.2 Log a WARNING and skip any watch-dir path that does not exist or is not a directory at config load time
- [x] 2.3 Add `ZETTELKASTEN_WATCH_DIRS` documentation to `README.md` environment-variables table

## 3. Watch-Folder Ingestion Service

- [x] 3.1 Create `src/zettelkasten_mcp/services/watch_folder_service.py` with a `WatchFolderService` class
- [x] 3.2 Implement `WatchFolderService.scan_directory(path: Path) -> list[Note]` — recursively finds `.md` files, parses YAML frontmatter (catches parse errors per-file), and returns a list of `Note` objects with `is_readonly=True` and `source_path` set
- [x] 3.3 Implement deterministic ID generation for frontmatter-absent files: `ext-<sha256(absolute_path)[:12]>` and title from filename stem
- [x] 3.4 Implement `WatchFolderService.sync_all() -> dict` — drops all `is_readonly=True` rows from the DB, re-scans all watch dirs, re-ingests, and returns a summary `{scanned, added, removed, errors}`
- [x] 3.5 Wire `WatchFolderService.sync_all()` call into server startup (after primary notes indexing) in `src/zettelkasten_mcp/main.py` or the server initialisation path

## 4. Read-Only Mutation Guards

- [x] 4.1 In `ZettelService.update_note()`, check `note.is_readonly` before proceeding; raise `PermissionError("Cannot modify read-only external note: <source_path>")` if true
- [x] 4.2 In `ZettelService.delete_note()`, check `is_readonly` on the retrieved note; raise `PermissionError` if true
- [x] 4.3 Ensure `ZettelService.create_link()` allows links targeting read-only notes without modification to the target note

## 5. MCP Server Tool

- [x] 5.1 Register `zk_sync_watch_folders` tool in `src/zettelkasten_mcp/server/mcp_server.py`
- [x] 5.2 Tool calls `WatchFolderService.sync_all()` and returns a formatted summary string (files scanned, notes added, notes removed, per-file errors)
- [x] 5.3 If `watch_dirs` is empty, return `"No watch directories configured."` without making any DB changes

## 6. Search & List Enhancements

- [x] 6.1 Ensure `NoteRepository.search()` and `NoteRepository.list_all()` include `is_readonly` and `source_path` in returned `Note` objects (mapped from DB columns)
- [x] 6.2 Add optional `include_external: bool = True` parameter to `zk_list_notes` MCP tool; when `False`, filter out notes where `is_readonly=True`
- [x] 6.3 Verify `zk_get_note` returns `is_readonly` and `source_path` in its response

## 7. Tests

- [x] 7.1 Create `tests/test_watch_folder_config.py` — test parsing of `ZETTELKASTEN_WATCH_DIRS` (single path, multiple paths, non-existent path warning, unset)
- [x] 7.2 Create `tests/test_watch_folder_service.py` — test `scan_directory()` with frontmatter-compatible files, frontmatter-absent files, malformed frontmatter, empty directory; test deterministic ID generation
- [x] 7.3 Add tests for `sync_all()` covering new file detection, deleted file removal, parse error reporting, and no-watch-dirs case
- [x] 7.4 Create `tests/test_watch_folder_readonly.py` — test mutation guards: update rejected, delete rejected, link-to-readonly allowed
- [x] 7.5 Add integration tests in `tests/test_integration.py` covering full startup-scan flow and the `zk_sync_watch_folders` MCP tool
- [x] 7.6 Add tests for `include_external` filter parameter in `zk_list_notes`
- [x] 7.7 Run full test suite and ensure all existing tests still pass (`uv run pytest -v`)

## 8. Documentation

- [x] 8.1 Update `README.md` with a "Watch Folders" section explaining the feature, configuration, and `zk_sync_watch_folders` tool
- [x] 8.2 Update the MCP tool listing in `README.md` to include `zk_sync_watch_folders`
- [x] 8.3 Update `CHANGELOG.md` with the new feature entry
