## Why

Currently the MCP server only manages notes in a single configured notes directory. Users often have existing Markdown files — documentation, reference material, project notes — stored in other folders that they want to cross-reference and link from their Zettelkasten. There is no way to index or link to those files without manually copying them into the notes directory, which breaks their original location and duplicates content.

## What Changes

- Add a new optional configuration option `ZETTELKASTEN_WATCH_DIRS` (a comma-separated list of directory paths) for specifying one or more external folders to index.
- On startup (and on demand), the server scans each watch directory recursively for Markdown files.
- Markdown files with compatible YAML frontmatter (containing at least an `id` or `title` field) are ingested into the SQLite index as read-only reference notes.
- Markdown files without compatible frontmatter are indexed by filename/path and made searchable, but treated as unstructured documents.
- Links from primary notes can reference indexed external files using their generated or declared ID.
- New notes created via MCP tools are always written to the primary notes directory (`ZETTELKASTEN_NOTES_DIR`).
- External watch-folder notes are marked read-only in the index — they cannot be modified or deleted through MCP tools.
- A new MCP tool `zk_sync_watch_folders` allows manual re-indexing of watch directories without restarting the server.

## Capabilities

### New Capabilities

- `watch-folder-indexing`: Scan one or more external Markdown directories, parse compatible frontmatter, and ingest files into the SQLite index as read-only reference notes. Expose indexed external notes via search and graph traversal alongside primary notes.
- `watch-folder-config`: Configuration support for `ZETTELKASTEN_WATCH_DIRS` — parsing, validation, and persistence of watch directory paths alongside existing config options.
- `watch-folder-sync`: MCP tool `zk_sync_watch_folders` that triggers a re-scan of all configured watch directories, updating the index with new, modified, or removed files without restarting the server.

### Modified Capabilities

- `core-enhancements`: The note retrieval and search APIs must distinguish between primary (writable) notes and external (read-only) watch-folder notes, surfacing source provenance in results.

## Impact

- **Config** (`src/zettelkasten_mcp/config.py`): New `watch_dirs` field — list of validated directory paths.
- **Storage** (`src/zettelkasten_mcp/storage/note_repository.py`): Ingest logic for external Markdown files; read-only flag in DB model.
- **DB Models** (`src/zettelkasten_mcp/models/db_models.py`): New `source` / `is_readonly` column on the `notes` table.
- **Schema** (`src/zettelkasten_mcp/models/schema.py`): `Note` model gains optional `source_path` and `is_readonly` fields.
- **MCP Server** (`src/zettelkasten_mcp/server/mcp_server.py`): New `zk_sync_watch_folders` tool; existing tools guard against mutating read-only notes.
- **Services** (`src/zettelkasten_mcp/services/zettel_service.py`): Watch-folder ingestion service; mutation guards.
- **Tests**: New test files covering ingestion, read-only enforcement, sync tool, and config parsing.
- **Dependencies**: No new third-party dependencies required (uses stdlib `pathlib`, `os`, existing `python-frontmatter`/YAML parsing already in use).
