# watch-folder-sync Specification

## Purpose
TBD - created by archiving change external-folder-indexing. Update Purpose after archive.
## Requirements
### Requirement: MCP tool zk_sync_watch_folders triggers re-indexing
The system SHALL expose a `zk_sync_watch_folders` MCP tool that, when called, performs a full re-scan of all configured watch directories without restarting the server. The sync SHALL remove all existing watch-folder entries from the SQLite index (rows where `is_readonly = True` and `source_path` is set), then re-ingest all currently present Markdown files from each watch directory applying the same ingestion rules as startup. The tool SHALL return a summary including: number of files scanned, number of notes added, number of notes removed (no longer present on disk), and any per-file errors encountered. If no watch directories are configured, the tool SHALL return a message indicating the feature is not configured.

#### Scenario: Sync discovers a new file added after startup
- **WHEN** a new Markdown file is placed in a watch directory after server startup
- **AND** `zk_sync_watch_folders` is called
- **THEN** the new file is ingested into the index
- **AND** the tool response reports 1 file added

#### Scenario: Sync removes entry for a deleted file
- **WHEN** a Markdown file previously in a watch directory is deleted from disk
- **AND** `zk_sync_watch_folders` is called
- **THEN** the corresponding index entry is removed
- **AND** the tool response reports 1 note removed

#### Scenario: Sync reports per-file errors without aborting
- **WHEN** one file in a watch directory has malformed frontmatter
- **AND** `zk_sync_watch_folders` is called
- **THEN** all other files are processed normally
- **AND** the tool response includes a list of files that encountered errors

#### Scenario: No watch dirs configured
- **WHEN** `zk_sync_watch_folders` is called and `watch_dirs` is empty
- **THEN** the tool returns a message: "No watch directories configured."
- **AND** no index changes are made

